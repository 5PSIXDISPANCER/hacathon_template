import ggwave
import pyaudio

# Настройки аудио
p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16, channels=1, rate=48000, output=True)

text_to_send = "Hello World!"
print(f"Кодирование и отправка текста: '{text_to_send}'")

# Генерируем аудио-сигнал из текста (по умолчанию используется протокол AUDIBLE_FAST)
waveform = ggwave.encode(text_to_send)

# Воспроизводим звук через динамики
stream.write(waveform)

# Корректное закрытие потоков
stream.stop_stream()
stream.close()
p.terminate()
print("Отправка завершена.")
