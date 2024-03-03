import os
import io
import pyaudio
from six.moves import queue
from google.cloud import speech
from google.oauth2 import service_account

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

def listen_print_loop(responses):
    """Iterates through server responses and prints them."""
    for response in responses:
        if not response.results:
            continue

        # Grab the first result from the list of results.
        result = response.results[0]

        # Check if the first alternative is available and the result is final.
        if result.alternatives and result.is_final:
            transcript = result.alternatives[0].transcript
            print(u"\nFinal Transcript: {}".format(transcript))

            # Here, you can add logic to act on the final transcript.
            if "hello world" in transcript.lower():
                print("Hello World to you too!")
                # Since it's a continuous listening loop, we don't return/break here,
                # but you can set a flag to stop listening if needed.


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
