import pyaudio

p = pyaudio.PyAudio()

def listen(format=pyaudio.paFloat32, channels=1, rate=48000, input=True, frames_per_buffer=1024):
    lising = p.open(format=format, channels=channels, rate=rate, input=True, frames_per_buffer=frames_per_buffer)
    try:
        while True:
            data = lising.read(1024, exception_on_overflow=False)
            return data
    except:
        pass
                