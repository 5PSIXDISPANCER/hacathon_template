import pyaudio
from gui.ui import App
# from ggwave import ...
p = pyaudio.PyAudio()


stream = p.open(format=App().show_progress_menu[0], channels=1 , rate = App().show_progress_menu[1], output=True, frames_per_buffer=App().show_progress_menu[2])
stream.write(waveform, len(waveform)//4)
stream.stop_stream()
stream.close()

p.terminate()