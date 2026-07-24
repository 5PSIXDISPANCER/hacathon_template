import numpy as np
import scipy.signal
from scipy.io import wavfile
import reedsolo
import sounddevice as sd
import os

# --- НАСТРОЙКИ МОДЕМА ---
FS = 44100
SYM_DUR = 0.08              # 80 мс на символ
K = 4                       # 4 частотных канала
F_BASE = 500                # Стартовая частота
CHANNEL_SPACING = 400       # Шаг между каналами
TONE_STEP = 25              # Шаг частот внутри канала
PREAMBLE = b'\xDE\xAD\xBE\xEF'
ECC_SYMBOLS = 16            # Защита Рида-Соломона

rs = reedsolo.RSCodec(ECC_SYMBOLS)

# Сколько байт полезных данных помещается в один пакет (кадр).
PAYLOAD_PER_FRAME = 64 


# --- 1. ГЕНЕРАТОР ОДНОГО КАДРА (Кодер) ---
def generate_frame_signal(chunk: bytes, frame_id: int) -> np.ndarray:
    """Оборачивает кусок данных в защищенный M-FSK пакет с номером кадра."""
    header = frame_id.to_bytes(2, byteorder='big')
    raw_packet = header + chunk
    
    protected_data = bytes(rs.encode(raw_packet))
    full_data = PREAMBLE + protected_data
    
    nibbles = []
    for byte in full_data:
        nibbles.append(byte >> 4)
        nibbles.append(byte & 0x0F)
        
    pad_len = (K - (len(nibbles) % K)) % K
    if pad_len > 0:
        nibbles.extend([0] * pad_len)
        
    num_symbols = len(nibbles) // K
    N_samples = int(FS * SYM_DUR)
    
    signal = np.zeros(num_symbols * N_samples, dtype=np.float64)
    t = np.arange(N_samples) / FS
    
    fade_len = int(FS * 0.002)
    window = np.ones(N_samples)
    if fade_len > 0:
        window[:fade_len] = np.linspace(0, 1, fade_len)
        window[-fade_len:] = np.linspace(1, 0, fade_len)

    for i in range(num_symbols):
        sym_nibbles = nibbles[i*K : (i+1)*K]
        sym_wave = np.zeros(N_samples, dtype=np.float64)
        
        for k_idx, nib in enumerate(sym_nibbles):
            freq = F_BASE + k_idx * CHANNEL_SPACING + nib * TONE_STEP
            sym_wave += np.sin(2 * np.pi * freq * t)
            
        sym_wave *= window
        signal[i*N_samples : (i+1)*N_samples] = sym_wave

    max_val = np.max(np.abs(signal))
    if max_val > 0:
        signal = signal / max_val
    return signal


# --- 2. ПОТОКОВЫЙ КОДЕР БОЛЬШИХ ФАЙЛОВ ---
def encode_large_file(input_file_path: str, output_wav_path: str):
    """Разбивает большой файл на пакеты и потоково пишет аудио в WAV."""
    if not os.path.exists(input_file_path):
        print(f"[-] Файл {input_file_path} не найден.")
        return 0
        
    file_size = os.path.getsize(input_file_path)
    print(f"[*] Исходный файл: {file_size} байт (~{file_size/1024:.1f} КБ)")
    
    audio_accumulator = []
    audio_accumulator.append(np.zeros(int(FS * 1.0))) # Тишина в начале
    
    frame_id = 0
    with open(input_file_path, 'rb') as f:
        while True:
            chunk = f.read(PAYLOAD_PER_FRAME)
            if not chunk:
                break
                
            if len(chunk) < PAYLOAD_PER_FRAME:
                chunk = chunk.ljust(PAYLOAD_PER_FRAME, b'\x00')
                
            frame_signal = generate_frame_signal(chunk, frame_id)
            audio_accumulator.append(frame_signal)
            audio_accumulator.append(np.zeros(int(FS * 0.005))) # Пауза между кадрами
            
            frame_id += 1
            if frame_id % 50 == 0:
                print(f"[+] Сгенерировано пакетов: {frame_id}...")

    audio_accumulator.append(np.zeros(int(FS * 1.0))) # Тишина в конце
    
    print("[*] Финализация: сохранение аудио на диск...")
    full_signal = np.concatenate(audio_accumulator)
    full_signal_int16 = (full_signal * 32767 * 0.8).astype(np.int16)
    
    wavfile.write(output_wav_path, FS, full_signal_int16)
    print(f"[✓] Аудиофайл успешно создан: {output_wav_path} (Длительность: {len(full_signal_int16)/FS:.1f} сек)")
    return file_size


# --- 3. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЕКОДЕРА ---
def bandpass_filter(samples, fs, lowcut, highcut, order=5):
    nyq = 0.5 * fs
    b, a = scipy.signal.butter(order, [lowcut / nyq, highcut / nyq], btype='band')
    return scipy.signal.filtfilt(b, a, samples)

def soft_demodulate(samples, fs, sym_dur, K_channels, freqs):
    N = int(fs * sym_dur)
    num_sym = len(samples) // N
    t = np.arange(N) / fs
    
    cos_ref = np.cos(2 * np.pi * freqs[:, :, None] * t)
    sin_ref = np.sin(2 * np.pi * freqs[:, :, None] * t)

    soft = []
    for sym_idx in range(num_sym):
        block = samples[sym_idx*N : (sym_idx+1)*N]
        I = np.dot(cos_ref, block)
        Q = np.dot(sin_ref, block)
        energy = I**2 + Q**2
        soft.append(energy)
    return np.array(soft)

def bytes_to_nibbles(bs):
    seq = []
    for byte in bs:
        seq.extend([byte >> 4, byte & 0x0F])
    return np.array(seq, dtype=int)

def find_flag_soft(soft, flag_nibbles, K_channels):
    L = len(flag_nibbles)
    syms_needed = int(np.ceil(L / K_channels))
    best_score = -1.0
    best_start = -1
    num_sym = soft.shape[0]
    
    for start in range(num_sym - syms_needed + 1):
        score = 0.0
        for off in range(syms_needed):
            sym = start + off
            for k in range(K_channels):
                pos = off * K_channels + k
                if pos < L:
                    score += soft[sym, k, flag_nibbles[pos]]
        if score > best_score:
            best_score = score
            best_start = start
    return best_start


# --- 4. ПОТОКОВЫЙ ДЕКОДЕР БОЛЬШИХ ФАЙЛОВ ---
def decode_large_file_from_samples(samples: np.ndarray, output_file_path: str, total_file_size: int):
    """Декодирует массив семплов (записанных с микрофона), исправляет ошибки и собирает файл."""
    sig = samples.astype(np.float64) / 32768.0

    lowcut = F_BASE - 50
    highcut = F_BASE + (K-1)*CHANNEL_SPACING + 15*TONE_STEP + 50
    sig = bandpass_filter(sig, FS, lowcut, highcut)

    freqs = np.array([[F_BASE + k*CHANNEL_SPACING + s*TONE_STEP for s in range(16)] for k in range(K)])
    soft = soft_demodulate(sig, FS, SYM_DUR, K, freqs)

    pre_nib = bytes_to_nibbles(PREAMBLE)
    
    packet_bytes_len = 2 + PAYLOAD_PER_FRAME + ECC_SYMBOLS 
    packet_nibbles_len = packet_bytes_len * 2
    pad_len_nibbles = (K - (packet_nibbles_len % K)) % K
    total_nibbles_per_packet = packet_nibbles_len + pad_len_nibbles
    syms_per_packet = total_nibbles_per_packet // K
    pre_syms = int(np.ceil(len(pre_nib) / K))

    expected_frames = int(np.ceil(total_file_size / PAYLOAD_PER_FRAME))
    reconstructed_data = bytearray()
    
    print(f"[*] Начинаем сборку файла ({expected_frames} пакетов)...")
    
    current_search_start = 0
    for frame_id in range(expected_frames):
        sub_soft = soft[current_search_start:]
        rel_start = find_flag_soft(sub_soft, pre_nib, K)
        
        if rel_start == -1:
            print(f"[-] Предупреждение: Не удалось найти кадр #{frame_id}")
            break
            
        start_sym = current_search_start + rel_start
        data_start = start_sym + pre_syms
        data_end = data_start + syms_per_packet
        
        nibbles = []
        for sym in range(data_start, data_end):
            if sym >= soft.shape[0]:
                break
            for k in range(K):
                nibbles.append(np.argmax(soft[sym, k]))

        raw_bytes = bytearray()
        for i in range(0, len(nibbles)-1, 2):
            raw_bytes.append((nibbles[i] << 4) | nibbles[i+1])

        try:
            decoded_packet, _, _ = rs.decode(bytes(raw_bytes[:packet_bytes_len]))
            chunk_data = decoded_packet[2:] # отрезаем frame_id
            reconstructed_data.extend(chunk_data)
        except Exception:
            print(f"[-] Ошибка FEC в кадре #{frame_id} (пакет поврежден)")
            reconstructed_data.extend(b'\x00' * PAYLOAD_PER_FRAME)
            
        current_search_start = data_end
        
        if (frame_id + 1) % 50 == 0:
            print(f"[+] Обработано пакетов: {frame_id + 1}/{expected_frames}...")

    final_data = bytes(reconstructed_data[:total_file_size])
    if os.path.dirname(output_file_path):
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
    
    with open(output_file_path, 'wb') as f:
        f.write(final_data)
    print(f"[✓] Файл успешно восстановлен: {output_file_path}")


# --- 5. ЗАПУСК ТЕСТА ЧЕРЕЗ ВОЗДУХ ---
if __name__ == "__main__":
    test_input = "test_file.bin"
    test_output = "restored_file.bin"

    # Создадим небольшой тестовый файл, если его нет
    if not os.path.exists(test_input):
        with open(test_input, "wb") as f:
            f.write(b"Hello! This is a binary stream test file transmitted through air via acoustic M-FSK modem." * 5)

    print(f"[*] Кодируем файл '{test_input}' в аудио...")
    wav_path = "temp_transmission.wav"
    file_size = encode_large_file(test_input, wav_path)

    if file_size > 0:
        # Загружаем сгенерированный WAV для проигрывания
        _, tx_signal = wavfile.read(wav_path)

        print("\n[*] ВНИМАНИЕ: Убедитесь, что динамик включен, а микрофон рядом.")
        print("[*] Воспроизведение и запись через воздух...")

        # Одновременный вывод на динамик и запись с микрофона
        rx_signal = sd.playrec(tx_signal, samplerate=FS, channels=1, dtype='int16', blocking=True)
        rx_signal = rx_signal.flatten()

        print("[+] Запись завершена. Декодируем аудиопоток в файл...")
        decode_large_file_from_samples(rx_signal, test_output, file_size)