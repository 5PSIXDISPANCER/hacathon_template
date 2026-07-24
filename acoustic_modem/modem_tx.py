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