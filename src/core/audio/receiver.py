import pyaudio
from gui.ui import App
# from ggwave import ...
p = pyaudio.PyAudio()

def Stream(format: int, rate: int,frames: int ):
    stream = p.open(format=format, channels=1 , rate = rate, output=True, frames_per_buffer=frames)
    stream.write(waveform, len(waveform)//4)
    stream.stop_stream()
    stream.close()

    p.terminate()