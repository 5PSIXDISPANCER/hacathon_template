import ggwave
import pyaudio

instance = ggwave.init()

p = pyaudio.PyAudio()
# ВАЖНО: формат паFloat32 и буфер побольше (4096), чтобы не терять пакеты
stream = p.open(format=pyaudio.paFloat32, channels=1, rate=48000, input=True, frames_per_buffer=4096)

print("Слушаю эфир (Float32)...")

try:
    while True:
        data = stream.read(4096, exception_on_overflow=False)
        
        # Декодируем float32 данные
        res = ggwave.decode(instance, data)
        
        if res is not None:
            print(f"\n[Получено]: {res.decode('utf-8')}")
except KeyboardInterrupt:
    pass
finally:
    ggwave.free(instance)
    stream.stop_stream()
    stream.close()
    p.terminate()
