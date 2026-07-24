import ggwave
import pyaudio

# Инициализируем движок ggwave
instance = ggwave.init()

# Настройки аудио (должны совпадать с отправителем)
p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16, channels=1, rate=48000, input=True, frames_per_buffer=1024)

print("Приниматель запущен. Слушаю эфир... (Нажмите Ctrl+C для выхода)")

try:
    while True:
        # Читаем данные с микрофона
        data = stream.read(1024, exception_on_overflow=False)
        
        # Передаем аудио-пакет в декодер ggwave
        res = ggwave.decode(instance, data)
        
        # Если ggwave успешно распознал маркеры и текст
        if res:
            try:
                decoded_text = res.decode("utf-8")
                print(f"\n[Успешно получено]: {decoded_text}")
            except Exception as e:
                print(f"\n Ошибка декодирования строки: {e}")
                
except KeyboardInterrupt:
    print("\nОстановка принимателя...")
finally:
    # Очистка ресурсов
    stream.stop_stream()
    stream.close()
    p.terminate()
