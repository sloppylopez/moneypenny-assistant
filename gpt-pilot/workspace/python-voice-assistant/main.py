import os
import io
import pyaudio
from six.moves import queue
from google.cloud import speech
from google.oauth2 import service_account
import subprocess   
import sys
import runpy
from os.path import dirname, abspath


# Audio recording parameters
RATE = 16000
CHUNK = int(RATE / 10)  # 100ms

class MicrophoneStream(object):
    """Opens a recording stream as a generator yielding the audio chunks."""
    def __init__(self, rate, chunk):
        self._rate = rate
        self._chunk = chunk
        self._buff = queue.Queue()
        self.closed = True

    def __enter__(self):
        self._audio_interface = pyaudio.PyAudio()
        self._audio_stream = self._audio_interface.open(
            format=pyaudio.paInt16,
            channels=1, rate=self._rate,
            input=True, frames_per_buffer=self._chunk,
            stream_callback=self._fill_buffer,
        )
        self.closed = False
        return self

    def __exit__(self, type, value, traceback):
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        self._buff.put(None)
        self._audio_interface.terminate()

    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
        """Continuously collect data from the audio stream, into the buffer."""
        self._buff.put(in_data)
        return None, pyaudio.paContinue

    def generator(self):
        while not self.closed:
            chunk = self._buff.get()
            if chunk is None:
                return
            data = [chunk]

            while True:
                try:
                    chunk = self._buff.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break

            yield b''.join(data)

# Create a speech client
credentials = service_account.Credentials.from_service_account_file(
    '/home/octo/Work/Creds/assitant-416116-698a6c4c3111.json')  # Update this path
client = speech.SpeechClient(credentials=credentials)

import subprocess

def listen_print_loop(responses):
    """Iterates through server responses and prints them."""
    for response in responses:
        if not response.results:
            continue

        result = response.results[0]

        if result.alternatives and result.is_final:
            transcript = result.alternatives[0].transcript
            print(u"\nFinal Transcript: {}".format(transcript))

            # Detect "create a project named" command.
            if "create a project named" in transcript.lower():
                # Extract the project name from the transcript.
                project_name = transcript.lower().split("create a project named")[-1].strip()
                print(f"Creating project: {project_name}")
                # runpy.run_path("/home/octo/Work/gpt-pilot/pilot/main.py")
                script_path = "/home/octo/Work/gpt-pilot/pilot/main.py" # This to to able to debug a different main.py and have correct path relative to that file
                script_dir = dirname(script_path)

                if script_dir not in sys.path:
                    sys.path.insert(0, script_dir)

                runpy.run_path(script_path)
                # Define the path to your shell script and include the project name as an argument.
                # script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts", "gpt-pilot-start")
                # try:
                #     # Call the shell script with the project name.
                #     subprocess.run([script_path, project_name], check=True)
                #     print("Shell script executed successfully.")
                # except subprocess.CalledProcessError as e:
                #     print(f"Error executing shell script: {e}")



def main():
    language_code = "en-US"  # a BCP-47 language tag

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=RATE,
        language_code=language_code,
    )

    streaming_config = speech.StreamingRecognitionConfig(
        config=config,
        interim_results=True
    )

    with MicrophoneStream(RATE, CHUNK) as stream:
        audio_generator = stream.generator()
        requests = (speech.StreamingRecognizeRequest(audio_content=content)
                    for content in audio_generator)

        responses = client.streaming_recognize(streaming_config, requests)

        listen_print_loop(responses)

if __name__ == '__main__':
    main()
