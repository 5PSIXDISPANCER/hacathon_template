import math
import struct
import pyaudio

# --- Настройки акустического канала (Должны совпадать с передатчиком) ---
SAMPLE_RATE = 44100
BAUD_RATE = 50
FREQ_0 = 2000.0
FREQ_1 = 4000.0
SAMPLES_PER_BIT = int(SAMPLE_RATE / BAUD_RATE)

# --- Настройки микрофона ---
CHUNK = 1024
FORMAT = pyaudio.paInt16 # 16-битный звук
CHANNELS = 1             # Моно
RECORD_SECONDS = 20      # Сколько секунд слушать эфир (увеличьте, если файл большой)

def goertzel_mag(samples, target_freq, sample_rate):
    """Алгоритм Гёрцеля (Чистый Python) для поиска мощности частоты."""
    n = len(samples)
    k = int(0.5 + (n * target_freq / sample_rate))
    omega = (2.0 * math.pi * k) / n
    cosine = math.cos(omega)
    coeff = 2.0 * cosine
    
    q1 = 0.0
    q2 = 0.0
    
    for x in samples:
        q0 = coeff * q1 - q2 + x
        q2 = q1
        q1 = q0
        
    return math.sqrt(q1**2 + q2**2 - q1 * q2 * coeff)

def record_audio():
    """Функция записи звука с микрофона."""
    p = pyaudio.PyAudio()

    print(f"🎤 Включаю микрофон... (Запись пошла, у вас {RECORD_SECONDS} секунд!)")
    
    # Открываем поток с микрофона
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=SAMPLE_RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    frames = []

    # Читаем данные с микрофона по кусочкам (чанкам)
    for _ in range(0, int(SAMPLE_RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK)
        frames.append(data)

    print("🛑 Запись завершена. Обработка данных...")

    stream.stop_stream()
    stream.close()
    p.terminate()

    # Склеиваем все куски в одни сырые байты
    return b''.join(frames)

def process_and_decode(raw_audio_bytes):
    """Декодирование сырых байтов аудио в файл."""
    # Распаковываем 16-битный звук в числа (Little-Endian)
    num_samples = len(raw_audio_bytes) // 2
    samples = struct.unpack(f"<{num_samples}h", raw_audio_bytes)

    print("🔎 Анализ частот (Алгоритм Гёрцеля)...")
    bits = []
    
    # Демодуляция (перевод звука в нули и единицы)
    for i in range(0, len(samples) - SAMPLES_PER_BIT, SAMPLES_PER_BIT):
        chunk = samples[i : i + SAMPLES_PER_BIT]
        
        mag0 = goertzel_mag(chunk, FREQ_0, SAMPLE_RATE)
        mag1 = goertzel_mag(chunk, FREQ_1, SAMPLE_RATE)
        
        # Сравниваем, какая частота звучит громче
        if mag1 > mag0:
            bits.append(1)
        else:
            bits.append(0)
            
    print(f"✅ Извлечено {len(bits)} бит. Поиск маркера 'SYNC'...")
    
    # Поиск синхро-маркера 'SYNC' (Выравнивание битов)
    sync_target = b'SYNC'
    sync_bits = []
    for byte in sync_target:
        for i in range(7, -1, -1):
            sync_bits.append((byte >> i) & 1)
            
    start_idx = -1
    for i in range(len(bits) - 32):
        if bits[i : i + 32] == sync_bits:
            start_idx = i
            break
            
    if start_idx == -1:
        print("❌ Ошибка: Маркер 'SYNC' не найден. Поднесите источник звука ближе к микрофону.")
        return
        
    print("🎯 Маркер 'SYNC' найден! Собираем файл...")
    
    # Отбрасываем тишину и шумы до начала передачи
    aligned_bits = bits[start_idx:]
    
    # Переводим биты обратно в байты
    byte_array = bytearray()
    for i in range(0, len(aligned_bits) - 7, 8):
        byte = 0
        for j in range(8):
            byte |= (aligned_bits[i + j] << (7 - j))
        byte_array.append(byte)
        
    # Парсинг пакета
    try:
        name_len = byte_array[4]
        name_end_idx = 5 + name_len
        filename = byte_array[5 : name_end_idx].decode('utf-8')
        
        size_bytes = byte_array[name_end_idx : name_end_idx + 4]
        file_size = struct.unpack('>I', size_bytes)[0]
        
        file_data = byte_array[name_end_idx + 4 : name_end_idx + 4 + file_size]
        
        output_name = f"auto_received_{filename}"
        with open(output_name, 'wb') as f:
            f.write(file_data)
            
        print("-" * 30)
        print("🎉 УСПЕХ! Данные раскодированы.")
        print(f"📁 Сохранено как: {output_name}")
        print(f"📊 Размер: {len(file_data)} байт")
        
    except Exception as e:
        print(f"❌ Ошибка сборки файла: {e}")

# ==========================================
# ЗАПУСК
# ==========================================
if __name__ == "__main__":
    # 1. Записываем звук (у вас будет 20 секунд, чтобы включить передачу)
    audio_data = record_audio()
    
    # 2. Декодируем записанное
    process_and_decode(audio_data)