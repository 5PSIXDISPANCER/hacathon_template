import pyaudio

# ПРИМЕЧАНИЕ: несмотря на имя файла (унаследовано от исходной структуры
# проекта), эта функция ВОСПРОИЗВОДИТ звук через колонки (output=True) —
# то есть по факту это сторона ПЕРЕДАЧИ. Настоящий приём/запись с микрофона
# находится в transmitter.py. Переименовывать файлы не стал, чтобы не
# ломать существующие импорты в main.py — но имейте это в виду.


def Stream(waveforms, rate: int, frames_per_buffer: int,
           audio_format=pyaudio.paFloat32, gap_seconds: float = 0.3):
    """
    Проигрывает одну волну или список волн (чанков) по очереди.

    waveforms: bytes ИЛИ list[bytes] — если передан список, чанки
               проигрываются последовательно с паузой gap_seconds между
               ними, чтобы приёмник успел отделить одно ggwave-сообщение
               от следующего.
    """
    if isinstance(waveforms, (bytes, bytearray)):
        waveforms = [waveforms]

    p = pyaudio.PyAudio()
    stream = p.open(
        format=audio_format,
        channels=1,
        rate=rate,
        output=True,
        frames_per_buffer=frames_per_buffer
    )

    bytes_per_sample = p.get_sample_size(audio_format)  # 4 байта для paFloat32
    silence_chunk = b"\x00" * bytes_per_sample

    try:
        last_idx = len(waveforms) - 1
        for idx, waveform in enumerate(waveforms):
            num_frames = len(waveform) // bytes_per_sample
            if num_frames > 0:
                stream.write(waveform, num_frames)

            if idx != last_idx and gap_seconds > 0:
                silence_frames = int(rate * gap_seconds)
                stream.write(silence_chunk * silence_frames, silence_frames)
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()
