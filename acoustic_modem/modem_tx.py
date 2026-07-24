import struct
import math

def make_multichannel_fsk_wav(
    data: bytes,
    num_carriers: int = 4,      # K
    fs: int = 44100,
    sym_dur: float = 0.05,      # длительность символа
    f_base: float = 500,        # нижняя частота первого канала
    channel_spacing: float = 400,  # расстояние между центрами каналов
    tone_step: float = 25,      # шаг между частотами внутри канала (16 тонов)
    amplitude: float = 0.9
) -> bytes:
    """
    Многоканальная 16‑FSK / упрощённый OFDM.
    Каждый поднесущий модулируется своим полубайтом.
    """
    K = num_carriers
    # Построим таблицу частот для каждого канала: channel[k][nibble] = частота
    freqs = []
    for k in range(K):
        base_k = f_base + k * channel_spacing
        freqs.append([base_k + s * tone_step for s in range(16)])

    n_samples = int(fs * sym_dur)
    # Амплитуда одной поднесущей (чтобы суммарный пик < 32767)
    max_amplitude = int(32767 * amplitude)
    sub_amplitude = max_amplitude // K   # простое деление

    # Преобразуем данные в поток полубайтов
    nibbles = []
    for byte in data:
        nibbles.append(byte >> 4)        # старший
        nibbles.append(byte & 0x0F)      # младший

    # Дополним до кратности K
    rem = len(nibbles) % K
    if rem != 0:
        nibbles.extend([0] * (K - rem))

    samples = []
    # Фазы для каждого канала (поддерживаются непрерывными между блоками)
    phases = [0.0] * K

    # Обрабатываем блоки по K полубайтов
    for block_start in range(0, len(nibbles), K):
        block = nibbles[block_start:block_start + K]
        # Для каждого отсчёта в символе
        for i in range(n_samples):
            value = 0.0
            for k in range(K):
                f = freqs[k][block[k]]
                # синусоида с текущей фазой
                value += math.sin(phases[k])
                # обновляем фазу
                phases[k] += 2 * math.pi * f / fs
                # нормируем фазу (необязательно, но полезно)
                if phases[k] > 2 * math.pi:
                    phases[k] -= 2 * math.pi
            # масштабируем и записываем
            sample = int(value * sub_amplitude)
            # клиппинг на всякий случай
            if sample > 32767:
                sample = 32767
            elif sample < -32768:
                sample = -32768
            samples.append(sample)

    # Упаковка в PCM 16-bit little-endian
    pcm_data = b''.join(struct.pack('<h', s) for s in samples)

    # Заголовок WAV
    data_size = len(pcm_data)
    header = struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF', 36 + data_size, b'WAVE',
        b'fmt ', 16, 1, 1, fs, fs * 2, 2, 16,
        b'data', data_size
    )
    return header + pcm_data

# Пример использования
with open('acoustic_modem\hru.txt', 'rb') as f:
    file_bytes = f.read()

wav_bytes = make_multichannel_fsk_wav(file_bytes, num_carriers=4)
with open('res.wav', 'wb') as f:
    f.write(wav_bytes)