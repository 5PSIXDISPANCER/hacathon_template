import wave
import struct
import math
from io import BytesIO
import sounddevice as sd
import numpy as np
import wave

duration = 5  # секунд
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

def bandpass_fir(samples, fs, lowcut, highcut, numtaps=101):
    """Простой полосовой КИХ-фильтр, оконное проектирование (окно Хэмминга)."""
    import math
    # Идеальный ФНЧ с частотой среза highcut
    def sinc(x):
        return 1.0 if x == 0 else math.sin(x)/x
    # Коэффициенты
    taps = []
    center = (numtaps - 1) / 2
    for i in range(numtaps):
        n = i - center
        # Идеальный фильтр: ФНЧ highcut минус ФНЧ lowcut
        b = (2*highcut/fs * sinc(2*math.pi*highcut/fs * n) -
             2*lowcut/fs * sinc(2*math.pi*lowcut/fs * n))
        # Окно Хэмминга
        w = 0.54 - 0.46 * math.cos(2*math.pi*i/(numtaps-1))
        taps.append(b * w)
    # Свёртка
    filtered = []
    for i in range(len(samples)):
        val = 0.0
        for j in range(numtaps):
            idx = i + j - center
            if 0 <= idx < len(samples):
                val += samples[idx] * taps[j]
        filtered.append(val)
    return filtered

def bytes_to_nibble_seq(bs):
    seq = []
    for byte in bs:
        seq.append(byte >> 4)
        seq.append(byte & 0x0F)
    return seq

def soft_find_preamble(soft_metrics, expected_nibbles, K):
    L = len(expected_nibbles)
    num_sym = len(soft_metrics)
    syms_needed = (L + K - 1) // K
    best_score = -1.0
    best_start = -1
    for start in range(num_sym - syms_needed + 1):
        score = 0.0
        valid = True
        for sym_off in range(syms_needed):
            sym_idx = start + sym_off
            if sym_idx >= num_sym:
                valid = False
                break
            for k in range(K):
                pos = sym_off * K + k
                if pos < L:
                    exp_nib = expected_nibbles[pos]
                    score += soft_metrics[sym_idx][k][exp_nib]
        if valid and score > best_score:
            best_score = score
            best_start = start
    return best_start

def decode_multichannel_fsk_soft(
    wav_bytes: bytes,
    fs: int = 44100,
    sym_dur: float = 0.05,
    K: int = 4,
    f_base: float = 500,
    channel_spacing: float = 400,
    tone_step: float = 25,
    preamble: bytes = b'\xDE\xAD\xBE\xEF',
    postamble: bytes = b'\xCA\xFE\xBA\xBE'
) -> bytes:
    # Чтение WAV и нормализация
    with wave.open(BytesIO(wav_bytes), 'rb') as wf:
        assert wf.getsampwidth() == 2 and wf.getnchannels() == 1
        file_fs = wf.getframerate()
        if file_fs != fs:
            print(f"Warning: sample rate {file_fs} != {fs}, using {file_fs}")
            fs = file_fs
        raw = wf.readframes(wf.getnframes())
        samples_int = struct.unpack(f"<{len(raw)//2}h", raw)
        samples = [s / 32768.0 for s in samples_int]

    # Полосовая фильтрация (очистка от шума)
    lowcut = f_base - 100
    highcut = f_base + (K-1)*channel_spacing + 15*tone_step + 100
    samples = bandpass_fir(samples, fs, lowcut, highcut)

    N = int(fs * sym_dur)
    num_sym = len(samples) // N

    # Таблицы частот и корреляционные таблицы (как раньше)
    freqs = [[f_base + k*channel_spacing + s*tone_step for s in range(16)] for k in range(K)]
    cos_tab = [[[math.cos(2*math.pi*freqs[k][s]*n/fs) for n in range(N)] for s in range(16)] for k in range(K)]
    sin_tab = [[[math.sin(2*math.pi*freqs[k][s]*n/fs) for n in range(N)] for s in range(16)] for k in range(K)]

    # Мягкая демодуляция всех символов (сохраняем энергии)
    soft_metrics = []
    for sym_idx in range(num_sym):
        start = sym_idx * N
        block = samples[start:start+N]
        sym_eng = []
        for k in range(K):
            ch_eng = []
            for s in range(16):
                I = Q = 0.0
                c_arr = cos_tab[k][s]
                s_arr = sin_tab[k][s]
                for n in range(N):
                    val = block[n]
                    I += val * c_arr[n]
                    Q += val * s_arr[n]
                ch_eng.append(I*I + Q*Q)
            sym_eng.append(ch_eng)
        soft_metrics.append(sym_eng)

    # Поиск преамбулы (начало)
    preamble_nibbles = bytes_to_nibble_seq(preamble)
    preamble_start_sym = soft_find_preamble(soft_metrics, preamble_nibbles, K)
    if preamble_start_sym == -1:
        return b''       # преамбула не найдена
    pre_syms = (len(preamble_nibbles) + K - 1) // K
    data_start_sym = preamble_start_sym + pre_syms

    # Поиск постамбулы (конец)
    postamble_nibbles = bytes_to_nibble_seq(postamble)
    post_search_space = soft_metrics[data_start_sym:]
    post_rel_start = soft_find_preamble(post_search_space, postamble_nibbles, K)
    if post_rel_start == -1:
        data_end_sym = num_sym
    else:
        data_end_sym = data_start_sym + post_rel_start

    # Жёсткое декодирование только данных между флагами
    nibbles = []
    for sym_idx in range(data_start_sym, data_end_sym):
        sym_eng = soft_metrics[sym_idx]
        for k in range(K):
            eng = sym_eng[k]
            best_n = 0
            best_e = eng[0]
            for s in range(1, 16):
                if eng[s] > best_e:
                    best_e = eng[s]
                    best_n = s
            nibbles.append(best_n)

    # Сборка байтов (игнорируем оставшийся одиночный nibble)
    bytes_out = bytearray()
    for i in range(0, len(nibbles)-1, 2):
        bytes_out.append((nibbles[i] << 4) | nibbles[i+1])
    return bytes(bytes_out)

with open('recorded.wav', 'rb') as f:
    wav_data = f.read()
original_bytes = decode_multichannel_fsk_soft(wav_data)
with open('decoded_output.bin', 'wb') as f:
    f.write(original_bytes)