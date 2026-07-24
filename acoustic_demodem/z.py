import wave
import struct
import math
from io import BytesIO
import sounddevice as sd
import numpy as np
import wave

duration = 3  # секунд
fs = 44100
sd.default.samplerate = fs
sd.default.channels = 1
sd.default.dtype = 'int16'

print("Запись...")
audio = sd.rec(int(duration * fs), blocking=True)
print("Готово!")

# audio — это numpy array int16
# Сохраняем в WAV
with wave.open('recorded.wav', 'wb') as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(fs)
    wf.writeframes(audio.tobytes())

from scipy.signal import butter, filtfilt

def bandpass_filter(samples, fs, lowcut, highcut, order=5):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return filtfilt(b, a, samples)   # filtfilt – нулевая фаза

def soft_demodulate(samples, fs, sym_dur, K, freqs):
    N = int(fs * sym_dur)
    num_sym = len(samples) // N
    # freqs: (K, 16)
    # Заранее создаём опорные сигналы: shape (K, 16, N)
    t = np.arange(N) / fs
    cos_ref = np.cos(2 * np.pi * freqs[:, :, None] * t)   # (K,16,N)
    sin_ref = np.sin(2 * np.pi * freqs[:, :, None] * t)

    soft = []   # список: для каждого символа – матрица (K,16) энергий
    for sym_idx in range(num_sym):
        block = samples[sym_idx*N : (sym_idx+1)*N]   # (N,)
        # Умножаем на все опорные колебания и суммируем по времени
        I = np.dot(cos_ref, block)   # (K,16)  – скалярное произведение по N
        Q = np.dot(sin_ref, block)   # (K,16)
        energy = I**2 + Q**2         # (K,16)
        soft.append(energy)
    return np.array(soft)   # (num_sym, K, 16)

def bytes_to_nibble_seq(bs):
    seq = []
    for byte in bs:
        seq.append(byte >> 4)
        seq.append(byte & 0x0F)
    return np.array(seq, dtype=int)

def find_flag_soft(soft, flag_nibbles, K):
    """
    soft: (num_sym, K, 16) – энергии
    flag_nibbles: (L,) – ожидаемые nibble
    Возвращает индекс символа начала флага (или -1, если не найдено)
    """
    L = len(flag_nibbles)
    syms_needed = int(np.ceil(L / K))
    # Строим ожидаемый энергетический шаблон: выбираем для каждого символа и канала энергии нужного nibble
    # Для быстрой свёртки развернём soft в одномерный поток энергий по каналам и символам
    # Энергия для каждого символа и канала: soft[sym, k, nibble] – это то, что мы хотим суммировать.
    # Проще всего перебором:
    best_score = -1.0
    best_start = -1
    num_sym = soft.shape[0]
    for start in range(num_sym - syms_needed + 1):
        score = 0.0
        valid = True
        for off in range(syms_needed):
            sym = start + off
            if sym >= num_sym:
                valid = False
                break
            for k in range(K):
                pos = off * K + k
                if pos < L:
                    score += soft[sym, k, flag_nibbles[pos]]
        if valid and score > best_score:
            best_score = score
            best_start = start
    return best_start

from scipy.io import wavfile

def decode_fsk_wav(
    wav_path_or_bytes,
    fs=44100,
    sym_dur=0.05,
    K=4,
    f_base=500,
    channel_spacing=400,
    tone_step=25,
    preamble=b'\xDE\xAD\xBE\xEF',
    postamble=b'\xCA\xFE\xBA\xBE'
):
    # Чтение WAV (можно передать путь к файлу или байтовый объект)
    if isinstance(wav_path_or_bytes, str):
        rate, samples = wavfile.read(wav_path_or_bytes)
    else:
        from io import BytesIO
        rate, samples = wavfile.read(BytesIO(wav_path_or_bytes))
    assert samples.dtype == np.int16, "Ожидался 16-битный PCM"
    if rate != fs:
        print(f"Warning: частота дискретизации {rate} != {fs}, используется {rate}")
        fs = rate

    # Нормализация
    sig = samples.astype(np.float64) / 32768.0

    # Полосовая фильтрация (убираем шум)
    lowcut = f_base - 50
    highcut = f_base + (K-1)*channel_spacing + 15*tone_step + 50
    sig = bandpass_filter(sig, fs, lowcut, highcut, order=5)

    # Таблица частот
    freqs = np.array([[f_base + k*channel_spacing + s*tone_step for s in range(16)]
                      for k in range(K)])

    # Мягкая демодуляция
    soft = soft_demodulate(sig, fs, sym_dur, K, freqs)   # (num_sym, K, 16)

    # Поиск преамбулы
    preamble_nib = bytes_to_nibble_seq(preamble)
    start_sym = find_flag_soft(soft, preamble_nib, K)
    if start_sym == -1:
        return b''
    pre_syms = int(np.ceil(len(preamble_nib) / K))
    data_start = start_sym + pre_syms

    # Поиск постамбулы
    post_nib = bytes_to_nibble_seq(postamble)
    post_rel_start = find_flag_soft(soft[data_start:], post_nib, K)
    if post_rel_start == -1:
        data_end = soft.shape[0]
    else:
        data_end = data_start + post_rel_start

    # Жёсткое решение для данных между флагами
    nibbles = []
    for sym in range(data_start, data_end):
        for k in range(K):
            best_n = np.argmax(soft[sym, k])   # индекс максимальной энергии
            nibbles.append(best_n)

    # Сборка байтов (игнорируем одиночный полубайт в конце)
    out = bytearray()
    for i in range(0, len(nibbles)-1, 2):
        out.append((nibbles[i] << 4) | nibbles[i+1])
    return bytes(out)

with open('recorded.wav', 'rb') as f:
    wav_data = f.read()
original_bytes = decode_fsk_wav(wav_data)
with open('decoded_output.bin', 'wb') as f:
    f.write(original_bytes)