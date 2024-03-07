import os
import pyaudio
from six.moves import queue
import sys
from google.cloud import speech
from google.oauth2 import service_account
import runpy  # Import runpy to run another Python script

# Audio recording parameters
RATE = 16000
CHUNK = int(RATE / 10)  # 100ms

class MicrophoneStream(object):
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

credentials = service_account.Credentials.from_service_account_file(
    '/home/octo/Work/Creds/assistant-416116-698a6c4c3111.json')
client = speech.SpeechClient(credentials=credentials)

def listen_print_loop(responses, stream):
    for response in responses:
        if not response.results:
            continue

        result = response.results[0]
        if result.alternatives and result.is_final:
            transcript = result.alternatives[0].transcript
            print(u"\nFinal Transcript: {}".format(transcript))
            break  # Exit after the first final result

    stream.closed = True  # Ensure the stream is closed properly

def start_recording():
    language_code = "en-US"

    streaming_config = speech.StreamingRecognitionConfig(
        config=speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=RATE,
            language_code=language_code,
        ),
        interim_results=True
    )

    with MicrophoneStream(RATE, CHUNK) as stream:
        audio_generator = stream.generator()
        requests = (speech.StreamingRecognizeRequest(audio_content=content)
                    for content in audio_generator)
        responses = client.streaming_recognize(streaming_config, requests)
        listen_print_loop(responses, stream)

def main():
    print("Recording started. Speak into the microphone.")
    start_recording()

    # After exiting the recording, run the main.py of the other project
    project_path = '/home/octo/Work/gpt-pilot/pilot/main.py'
    runpy.run_path(project_path)

if __name__ == '__main__':
    main()
