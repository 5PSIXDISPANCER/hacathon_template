import pyaudio
# from ggwave import ...
p = pyaudio.PyAudio()

def Stream(rate: int,frames: int, format: int = pyaudio.paInt16):
    stream = p.open(format=format, channels=1 , rate = rate, output=True, frames_per_buffer=frames)
    stream.write(waveform, len(waveform)//4)
    stream.stop_stream()
    stream.close()

    p.terminate()