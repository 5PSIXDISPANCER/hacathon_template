import numpy as np
from scipy.io import wavfile

import numpy as np

import numpy as np

def make_multichannel_fsk_wav_ultra(
    data: bytes,
    num_carriers: int = 4,
    fs: int = 44100,
    sym_dur: float = 0.05,
    f_base: float = 500,
    channel_spacing: float = 400,
    tone_step: float = 25,
    amplitude: float = 0.9,
    preamble: bytes = b'\xDE\xAD\xBE\xEF',
    postamble: bytes = b'\xCA\xFE\xBA\xBE'
) -> np.ndarray:
    """
    Ультра-быстрая генерация. Расчет фазы через кумулятивное суммирование 
    без трехмерных матриц и чанков. Берет синус один раз от готового вектора.
    """
    K = num_carriers
    N = int(fs * sym_dur)
    max_amp = int(32767 * amplitude)
    sub_amp = max_amp // K

    # 1. Таблица частот
    freqs = np.array([
        [f_base + k*channel_spacing + s*tone_step for s in range(16)]
        for k in range(K)
    ], dtype=np.float32)

    # 2. Перевод в полубайты
    full_data = np.frombuffer(preamble + data + postamble, dtype=np.uint8)
    nibbles = np.empty(len(full_data) * 2, dtype=np.int64)
    nibbles[0::2] = full_data >> 4
    nibbles[1::2] = full_data & 0x0F

    rem = len(nibbles) % K
    if rem:
        nibbles = np.concatenate([nibbles, np.zeros(K - rem, dtype=np.int64)])
    
    num_blocks = len(nibbles) // K
    nibbles = nibbles.reshape(num_blocks, K)

    # 3. Выборка частот для всех блоков сразу (Shape: num_blocks x K)
    f_blocks = freqs[np.arange(K), nibbles]

    # 4. Формируем мгновенный шаг частоты для каждого отсчета времени
    # Вместо создания огромной сетки, мы просто повторяем частоты N раз
    # f_samples_per_carrier будет иметь форму (num_blocks * N, K)
    f_samples_per_carrier = np.repeat(f_blocks, N, axis=0)

    # 5. Интегрируем частоту для получения непрерывной фазы
    # Формула фазы: Phase = 2 * pi * sum(f / fs)
    # Превращаем частоты в шаги фазы на один сэмпл
    phase_steps = (2 * np.pi / fs) * f_samples_per_carrier
    
    # Кумулятивная сумма по оси времени генерирует идеальную непрерывную фазу!
    # Больше никаких стыков символов и никаких сложных матриц.
    # Shape: (total_samples, K)
    phases = np.cumsum(phase_steps, axis=0, dtype=np.float32)

    # 6. Модуляция: один раз берем синус от всей матрицы и суммируем каналы
    # np.sin(phases) -> Shape: (total_samples, K)
    # np.sum(..., axis=1) складывает K поднесущих вместе -> Shape: (total_samples,)
    signal = np.sum(np.sin(phases), axis=1)

    # 7. Масштабирование и клиппинг
    signal = signal * sub_amp
    return np.clip(signal, -32768, 32767).astype(np.int16)


# Пример использования
with open('acoustic_modem\ServerWrapperInline.jar', 'rb') as f:
    data = f.read()

print("end read")
signal = make_multichannel_fsk_wav_ultra(data)
print("end")
wavfile.write('res.wav', 44100, signal)
