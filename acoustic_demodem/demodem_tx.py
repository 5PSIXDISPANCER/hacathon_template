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

def decode_multichannel_fsk(
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
    """
    Декодер многоканальной 16-FSK с флагами.
    Возвращает полезные данные между preamble и postamble.
    Если флаги не найдены, возвращает пустую строку.
    """
    # --- Чтение WAV ---
    with wave.open(BytesIO(wav_bytes), 'rb') as wf:
        assert wf.getsampwidth() == 2, "16-bit PCM expected"
        assert wf.getnchannels() == 1, "Mono expected"
        file_fs = wf.getframerate()
        if file_fs != fs:
            print(f"Warning: WAV sample rate {file_fs} != expected {fs}, using {file_fs}")
            fs = file_fs
        raw = wf.readframes(wf.getnframes())
        fmt = f"{len(raw)//2}h"
        samples_int = struct.unpack(fmt, raw)
        samples = [s / 32768.0 for s in samples_int]

    N = int(fs * sym_dur)
    num_symbols = len(samples) // N

    # --- Частотные таблицы ---
    freqs = []
    for k in range(K):
        base_k = f_base + k * channel_spacing
        freqs.append([base_k + s * tone_step for s in range(16)])

    # --- Предвычисление корреляционных таблиц ---
    cos_tables = [[[0.0]*N for _ in range(16)] for _ in range(K)]
    sin_tables = [[[0.0]*N for _ in range(16)] for _ in range(K)]
    for k in range(K):
        for s in range(16):
            f = freqs[k][s]
            for n in range(N):
                phase = 2 * math.pi * f * n / fs
                cos_tables[k][s][n] = math.cos(phase)
                sin_tables[k][s][n] = math.sin(phase)

    # --- Демодуляция всех символов в полубайты ---
    decoded_nibbles = []
    for sym_idx in range(num_symbols):
        start = sym_idx * N
        block = samples[start:start+N]
        for k in range(K):
            max_energy = -1.0
            best_nibble = 0
            for s in range(16):
                I = Q = 0.0
                cos_arr = cos_tables[k][s]
                sin_arr = sin_tables[k][s]
                for n in range(N):
                    val = block[n]
                    I += val * cos_arr[n]
                    Q += val * sin_arr[n]
                energy = I*I + Q*Q
                if energy > max_energy:
                    max_energy = energy
                    best_nibble = s
            decoded_nibbles.append(best_nibble)

    # --- Сборка байтов из полубайтов ---
    all_bytes = bytearray()
    for i in range(0, len(decoded_nibbles) - 1, 2):
        high = decoded_nibbles[i]
        low = decoded_nibbles[i+1]
        all_bytes.append((high << 4) | low)

    # --- Поиск флагов ---
    start_idx = all_bytes.find(preamble)
    if start_idx == -1:
        return b''          # преамбула не найдена

    start_idx += len(preamble)
    end_idx = all_bytes.find(postamble, start_idx)
    if end_idx == -1:
        # если конец не найден, берём всё до конца
        return bytes(all_bytes[start_idx:])

    return bytes(all_bytes[start_idx:end_idx])

with open('recorded.wav', 'rb') as f:
    wav_data = f.read()
original_bytes = decode_multichannel_fsk(wav_data)
with open('decoded_output.bin', 'wb') as f:
    f.write(original_bytes)