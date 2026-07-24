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
    tone_step: float = 25
) -> bytes:
    """
    Декодер многоканальной 16-FSK.
    Параметры должны совпадать с модулятором.
    Возвращает исходные байты (без учёта возможного дополнения нулями в конце).
    """
    # === Чтение WAV ===
    with wave.open(BytesIO(wav_bytes), 'rb') as wf:
        assert wf.getsampwidth() == 2, "Ожидается 16-битный PCM"
        assert wf.getnchannels() == 1, "Ожидается моно"
        frame_rate = wf.getframerate()
        # Можно разрешить небольшое расхождение частоты дискретизации
        if frame_rate != fs:
            print(f"Предупреждение: Fs в WAV ({frame_rate}) != ожидаемой ({fs}). Используется {frame_rate}")
            fs = frame_rate

        raw_data = wf.readframes(wf.getnframes())
        # Распаковываем 16-битные знаковые целые
        fmt = f"{len(raw_data)//2}h"
        samples_int = struct.unpack(fmt, raw_data)
        # Нормализация к диапазону [-1, 1]
        samples = [s / 32768.0 for s in samples_int]

    # === Параметры символа ===
    N = int(fs * sym_dur)                     # отсчётов на символ
    num_symbols = len(samples) // N           # полных символов

    # === Таблица частот (как в модуляторе) ===
    freqs = []
    for k in range(K):
        base_k = f_base + k * channel_spacing
        freqs.append([base_k + s * tone_step for s in range(16)])

    # === Предвычисление sin/cos таблиц для всех каналов, тонов и отсчётов ===
    # Это значительно ускоряет вычисление корреляций
    cos_tables = [[[0.0]*N for _ in range(16)] for _ in range(K)]
    sin_tables = [[[0.0]*N for _ in range(16)] for _ in range(K)]

    for k in range(K):
        for s in range(16):
            f = freqs[k][s]
            for n in range(N):
                phase = 2 * math.pi * f * n / fs
                cos_tables[k][s][n] = math.cos(phase)
                sin_tables[k][s][n] = math.sin(phase)

    # === Декодирование ===
    decoded_nibbles = []
    for sym_idx in range(num_symbols):
        start = sym_idx * N
        block = samples[start:start+N]

        # Декодируем каждый канал
        for k in range(K):
            max_energy = -1.0
            best_nibble = 0
            for s in range(16):
                # Корреляция с cos и sin на частоте f_s
                I = 0.0
                Q = 0.0
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

    # === Сборка байтов ===
    # Игнорируем последний нечётный полубайт (если есть)
    byte_list = []
    for i in range(0, len(decoded_nibbles) - 1, 2):
        high = decoded_nibbles[i]
        low = decoded_nibbles[i+1]
        byte_list.append((high << 4) | low)

    return bytes(byte_list)

with open('recorded.wav', 'rb') as f:
    wav_data = f.read()
original_bytes = decode_multichannel_fsk(wav_data)
with open('decoded_output.bin', 'wb') as f:
    f.write(original_bytes)