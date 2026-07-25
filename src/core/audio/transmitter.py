import time
import pyaudio
import ggwave

from core.ggwave import converter

# ПРИМЕЧАНИЕ: несмотря на имя файла, эта функция ЗАПИСЫВАЕТ звук с
# микрофона (input=True) — то есть по факту это сторона ПРИЁМА.
# Воспроизведение (передача) находится в receiver.py. Имена файлов не
# менял, чтобы не ломать импорты в main.py.


def listen(rate: int = 48000, frames_per_buffer: int = 1024,
           total_timeout: float = 60.0, silence_timeout: float = 15.0):
    """
    Слушает микрофон и декодирует ggwave-чанки, пока не соберёт все части
    файла, либо пока не истечёт таймаут.

    total_timeout   — сколько ждать ПЕРВЫЙ чанк, прежде чем сдаться (сек).
    silence_timeout — после получения первого чанка: если следующий не
                       пришёл столько секунд подряд — считаем передачу
                       оборванной и прекращаем ждать остальные.

    Возвращает собранные бинарные данные исходного файла (bytes),
    либо None, если не удалось получить ни одного чанка.
    """
    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paFloat32,
        channels=1,
        rate=rate,
        input=True,
        frames_per_buffer=frames_per_buffer
    )

    instance = ggwave.init()
    chunks = {}
    total_expected = None
    start_time = time.time()
    last_received = start_time

    try:
        while True:
            data = stream.read(frames_per_buffer, exception_on_overflow=False)
            result = converter.decode_chunk(instance, data)

            if result is not None:
                index, total, chunk_bytes = result
                if index not in chunks:
                    chunks[index] = chunk_bytes
                    print(f"Получен чанк {index + 1}/{total}")
                total_expected = total
                last_received = time.time()

                if len(chunks) >= total_expected:
                    break

            now = time.time()
            if total_expected is None and (now - start_time) > total_timeout:
                print("Таймаут: не получено ни одного чанка")
                break
            if total_expected is not None and (now - last_received) > silence_timeout:
                print(f"Таймаут: получено {len(chunks)} из {total_expected} чанков, передача прервана")
                break
    finally:
        ggwave.free(instance)
        stream.stop_stream()
        stream.close()
        p.terminate()

    if not chunks or total_expected is None:
        return None

    # Склеиваем по порядку индексов. Если каких-то чанков не хватает —
    # результат будет повреждён, но мы всё равно возвращаем то, что есть,
    # чтобы вызывающий код мог хотя бы попытаться и сообщить об ошибке.
    ordered = [chunks[i] for i in range(total_expected) if i in chunks]
    return b"".join(ordered)
