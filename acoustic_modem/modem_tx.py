<<<<<<< HEAD
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
=======
import numpy as np
from scipy.io import wavfile
import reedsolo
import os

# --- НАСТРОЙКИ МОДЕМА (Должны строго совпадать у кодера и декодера) ---
FS = 44100
SYM_DUR = 0.08              # 80 мс на символ (устойчивость к эху)
K = 4                       # 4 частотных канала одновременно
F_BASE = 500                # Стартовая частота
CHANNEL_SPACING = 400       # Шаг между каналами (Гц)
TONE_STEP = 25              # Шаг между 16 значениями внутри канала (Гц)
PREAMBLE = b'\xDE\xAD\xBE\xEF'
POSTAMBLE = b'\xCA\xFE\xBA\xBE'
ECC_SYMBOLS = 16            # Количество проверочных байт Рида-Соломона на блок

rs = reedsolo.RSCodec(ECC_SYMBOLS)

def encode_fsk_wav(data: bytes, output_filename: str, amplitude: float = 0.8):
    # 1. Защита данных (FEC)
    # Преамбулу и постамбулу не кодируем, чтобы декодер мог легко их найти по энергии
    protected_data = bytes(rs.encode(data))
    full_data = PREAMBLE + protected_data + POSTAMBLE
    
    print(f"[*] Исходный размер: {len(data)} байт")
    print(f"[*] Размер с учетом FEC: {len(protected_data)} байт")

    # 2. Разбивка на полубайты (nibbles)
    nibbles = []
    for byte in full_data:
        nibbles.append(byte >> 4)      # Старшие 4 бита
        nibbles.append(byte & 0x0F)    # Младшие 4 бита
        
    # Выравнивание под количество каналов
    pad_len = (K - (len(nibbles) % K)) % K
    if pad_len > 0:
        nibbles.extend([0] * pad_len)
        
    num_symbols = len(nibbles) // K
    N_samples = int(FS * SYM_DUR)
    
    # Буфер сигнала
    signal = np.zeros(num_symbols * N_samples, dtype=np.float64)
    t = np.arange(N_samples) / FS
    
    # Окно сглаживания (чтобы динамик не щелкал)
    fade_len = int(FS * 0.002) # 2 мс
    window = np.ones(N_samples)
    if fade_len > 0:
        window[:fade_len] = np.linspace(0, 1, fade_len)
        window[-fade_len:] = np.linspace(1, 0, fade_len)

    # 3. Синтез частот
    for i in range(num_symbols):
        sym_nibbles = nibbles[i*K : (i+1)*K]
        sym_wave = np.zeros(N_samples, dtype=np.float64)
        
        for k_idx, nib in enumerate(sym_nibbles):
            freq = F_BASE + k_idx * CHANNEL_SPACING + nib * TONE_STEP
            sym_wave += np.sin(2 * np.pi * freq * t)
            
        sym_wave *= window
        signal[i*N_samples : (i+1)*N_samples] = sym_wave

    # 4. Нормализация и сохранение
    max_val = np.max(np.abs(signal))
    if max_val > 0:
        signal = signal / max_val
        
    wav_data = (signal * 32767 * amplitude).astype(np.int16)
    wavfile.write(output_filename, FS, wav_data)
    print(f"[+] Файл '{output_filename}' успешно сгенерирован!\n")


if __name__ == "__main__":
    # Тестовый запуск
    message = b"Hello, this is a highly reliable acoustic message protected by Reed-Solomon FEC!"
    encode_fsk_wav(message, "tx_signal.wav")
>>>>>>> 48d636cabb2395c56f6305f87bf1d43240ea7010
