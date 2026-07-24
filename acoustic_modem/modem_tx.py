import struct
import math

def make_multichannel_fsk_wav(
    data: bytes,
    num_carriers: int = 4,
    fs: int = 44100,
    sym_dur: float = 0.05,
    f_base: float = 500,
    channel_spacing: float = 400,
    tone_step: float = 25,
    amplitude: float = 0.9,
    preamble: bytes = b'\xDE\xAD\xBE\xEF',   # флаг начала (4 байта)
    postamble: bytes = b'\xCA\xFE\xBA\xBE'   # флаг конца
) -> bytes:
    """
    Многоканальная 16-FSK с флагами начала и конца.
    preamble и postamble могут быть любой длины, по умолчанию 4 байта.
    """
    K = num_carriers

    # --- Таблица частот (как раньше) ---
    freqs = []
    for k in range(K):
        base_k = f_base + k * channel_spacing
        freqs.append([base_k + s * tone_step for s in range(16)])

    n_samples = int(fs * sym_dur)
    max_amplitude = int(32767 * amplitude)
    sub_amplitude = max_amplitude // K

    # --- Формирование полных данных: preamble + полезные данные + postamble ---
    full_data = preamble + data + postamble

    # --- Преобразование в поток полубайтов ---
    nibbles = []
    for byte in full_data:
        nibbles.append(byte >> 4)          # старший
        nibbles.append(byte & 0x0F)        # младший

    # Дополнение до кратности K (чтобы последний блок был полным)
    rem = len(nibbles) % K
    if rem != 0:
        nibbles.extend([0] * (K - rem))

    # --- Модуляция ---
    samples = []
    phases = [0.0] * K

    for block_start in range(0, len(nibbles), K):
        block = nibbles[block_start:block_start + K]
        for i in range(n_samples):
            value = 0.0
            for k in range(K):
                f = freqs[k][block[k]]
                value += math.sin(phases[k])
                phases[k] += 2 * math.pi * f / fs
                if phases[k] > 2 * math.pi:
                    phases[k] -= 2 * math.pi
            sample = int(value * sub_amplitude)
            if sample > 32767:
                sample = 32767
            elif sample < -32768:
                sample = -32768
            samples.append(sample)

    # --- Упаковка в WAV ---
    pcm_data = b''.join(struct.pack('<h', s) for s in samples)
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