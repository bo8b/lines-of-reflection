from __future__ import division
from fuzzywuzzy import fuzz

import re
import sys
import os
import io
import pyaudio
import numpy as np

from google.cloud import speech
from google.cloud.speech import enums
from google.cloud.speech import types
from google.cloud import texttospeech

from six.moves import queue

# Setup application credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/home/pi/MagicMirror/modules/lines/Google API/lines-of-reflection-e981c0246ee8.json"
# Audio recording parameters
RATE = 16000
CHUNK = int(RATE / 10)  # 100ms


class MicrophoneStream(object):
    """Opens a recording stream as a generator yielding the audio chunks."""

    def __init__(self, rate, chunk):
        self._rate = rate
        self._chunk = chunk

        # Create a thread-safe buffer of audio data
        self._buff = queue.Queue()
        self.closed = True

    def __enter__(self):
        self._audio_interface = pyaudio.PyAudio()
        self._audio_stream = self._audio_interface.open(
            format=pyaudio.paInt16,
            # The API currently only supports 1-channel (mono) audio
            # https://goo.gl/z757pE
            channels=1,
            rate=self._rate,
            input=True,
            frames_per_buffer=self._chunk,
            # Run the audio stream asynchronously to fill the buffer object.
            # This is necessary so that the input device's buffer doesn't
            # overflow while the calling thread makes network requests, etc.
            stream_callback=self._fill_buffer,
        )

        self.closed = False

        return self

    def __exit__(self, type, value, traceback):
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        # Signal the generator to terminate so that the client's
        # streaming_recognize method will not block the process termination.
        self._buff.put(None)
        self._audio_interface.terminate()

    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
        """Continuously collect data from the audio stream, into the buffer."""
        self._buff.put(in_data)
        return None, pyaudio.paContinue

    def generator(self):
        while not self.closed:
            # Use a blocking get() to ensure there's at least one chunk of
            # data, and stop iteration if the chunk is None, indicating the
            # end of the audio stream.
            chunk = self._buff.get()
            if chunk is None:
                return
            data = [chunk]

            # Now consume whatever other data's still buffered.
            while True:
                try:
                    chunk = self._buff.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break

            yield b"".join(data)

def read_line(text_to_speak):
    # Instantiates a client
    client = texttospeech.TextToSpeechClient()

    # Set the text input to be synthesized
    #synthesis_input = texttospeech.SynthesisInput(text=text_to_speak)
    synthesis_input = texttospeech.types.SynthesisInput(text="Hello World")

    # Build the voice request, select the language code ("en-US") and the ssml
    # voice gender ("neutral")
    voice = texttospeech.types.VoiceSelectionParams(
        language_code="en-US", ssml_gender=texttospeech.enums.SsmlVoiceGender.NEUTRAL
    )

    # Select the type of audio file you want returned
    audio_config = texttospeech.types.AudioConfig(
        audio_encoding=texttospeech.enums.AudioEncoding.MP3
    )

    # Perform the text-to-speech request on the text input with the selected
    # voice parameters and audio file type
    response = client.synthesize_speech(
        input_=synthesis_input, voice=voice, audio_config=audio_config
    )


def lines_of_reflection():
    # Setup script
    script = np.genfromtxt("/home/pi/MagicMirror/modules/lines/script.csv", delimiter = ",", autostrip = True, dtype = "string")
    role = open("/home/pi/MagicMirror/modules/lines/role.txt", "r").read().strip()
    #print(script.shape)

    # See http://g.co/cloud/speech/docs/languages
    # for a list of supported languages.
    language_code = "en-US"  # a BCP-47 language tag

    client = speech.SpeechClient()
    config = types.RecognitionConfig(
        encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=RATE,
        language_code="en-US",
        max_alternatives = 1,
    )

    streaming_config = types.StreamingRecognitionConfig(
        config=config, interim_results=True
    )

    with MicrophoneStream(RATE, CHUNK) as stream:
        audio_generator = stream.generator()
        requests = (
            types.StreamingRecognizeRequest(audio_content=content)
            for content in audio_generator
        )

        responses = client.streaming_recognize(streaming_config, requests)

        # Loop through the script.  If not your role, display line, else check voice input with script
        for line in range(script.shape[0]):
            if script[line, 0].replace(":", "") != role:
                print(script[line, 0] + " " + script[line, 1])
                read_line(script[line,1])
                #print(script[line, 1])
            else:
                # Now, put the transcription responses to use.
                #listen_print_loop(responses)
                for response in responses:
                    if not response.results:
                        continue

		    # The `results` list is consecutive. For streaming, we only care about
		    # the first result being considered, since once it's `is_final`, it
		    # moves on to considering the next utterance.
                    result = response.results[0]
                    if not result.alternatives:
                        continue

		    # Display the transcription of the top alternative.
                    transcript = result.alternatives[0].transcript

                    if result.is_final:
                        if fuzz.token_sort_ratio(transcript.encode("ascii", "ignore"), script[line, 1]) >= 60:
                            print(script[line, 0] + " " + script[line, 1])
                            break
                        else:
                            print("I heard this:  ", transcript.encode("ascii", "ignore"), " - Accuracy: ", fuzz.token_sort_ratio(transcript.encode("ascii", "ignore"), script[line, 1]))
                            print("Please try again.")
		    # Exit or Calling for Line
                    if re.search(r"\b(computer exit|computer quit)\b", transcript, re.I):
                        print("Exiting..")
                        return False
                    elif re.search(r"\b(line please)\b", transcript, re.I):
                        print(script[line, 0] + " " + script[line, 1])


def main():
    lines_of_reflection()


if __name__ == "__main__":
    main()


