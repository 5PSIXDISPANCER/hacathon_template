import ggwave
import pyaudio

p = pyaudio.PyAudio()
# Переключаем формат на paFloat32
stream = p.open(format=pyaudio.paFloat32, channels=1, rate=48000, output=True)

text_to_send = "Hello World!"
print(f"Отправка текста: '{text_to_send}'")

# Принудительно генерируем waveform в формате float32
waveform = ggwave.encode(text_to_send, protocolId=ggwave.PROTOCOL_AUDIBLE_FAST)

stream.write(waveform)

stream.stop_stream()
stream.close()
p.terminate()
print("Готово.")
