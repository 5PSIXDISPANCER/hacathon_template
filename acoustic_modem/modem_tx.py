import os
import struct
import math
import wave

# --- Настройки акустического канала ---
SAMPLE_RATE = 44100  # Стандартная частота дискретизации аудио
BAUD_RATE = 50       # Скорость передачи: 50 бит в секунду
FREQ_0 = 2000.0      # Частота (Гц), обозначающая бит '0'
FREQ_1 = 4000.0      # Частота (Гц), обозначающая бит '1'

BIT_DURATION = 1.0 / BAUD_RATE
SAMPLES_PER_BIT = int(SAMPLE_RATE * BIT_DURATION)

def encode_file_to_bits(filepath):
    """
    Читает любой файл, собирает пакет (Заголовок + Данные) 
    и превращает его в плоский список нулей и единиц.
    """
    print(f"📦 Подготовка файла: '{filepath}'")
    
    # 1. Читаем бинарные данные файла
    with open(filepath, 'rb') as f:
        file_data = f.read()
        
    file_size = len(file_data)
    # Получаем имя файла и переводим в байты (UTF-8)
    filename_bytes = os.path.basename(filepath).encode('utf-8')
    
    # 2. Формируем структуру протокола (Служебная информация + Данные)
    # Используем встроенный модуль struct для упаковки чисел в байты
    sync_marker = b'SYNC'                                   # 4 байта: Маркер начала
    name_length = struct.pack('B', len(filename_bytes))     # 1 байт: Длина имени
    size_bytes = struct.pack('>I', file_size)               # 4 байта: Размер файла
    
    # Склеиваем всё в один пакет
    packet = sync_marker + name_length + filename_bytes + size_bytes + file_data
    
    print(f"📊 Размер исходного файла: {file_size} байт")
    print(f"📈 Общий размер пакета с заголовком: {len(packet)} байт")
    
    # 3. Разбиваем байты на биты (от старшего к младшему)
    bits = []
    for byte in packet:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
            
    print(f"✅ Сгенерировано {len(bits)} бит.")
    return bits

def generate_wav_from_bits(bits, output_wav="transmit.wav"):
    """
    Берет массив битов и синтезирует из них звуковую волну (синусоиду).
    Сохраняет результат в стандартный .wav файл без использования внешних библиотек.
    """
    print(f"🎵 Генерация аудиофайла '{output_wav}'...")
    
    # Открываем WAV файл для записи 
    # (1 канал - моно, 2 байта - 16-bit звук, 44100 Гц)
    with wave.open(output_wav, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        
        # Для каждого бита генерируем звук нужной частоты
        for bit in bits:
            freq = FREQ_1 if bit == 1 else FREQ_0
            
            # Генерируем сэмплы (точки звуковой волны) для одного бита
            for i in range(SAMPLES_PER_BIT):
                # Формула синусоиды: A * sin(2 * pi * f * t)
                time = i / SAMPLE_RATE
                # 32767 - максимальная амплитуда для 16-битного звука
                sample_value = int(32767 * math.sin(2 * math.pi * freq * time))
                
                # Упаковываем число в 2 байта (формат 'h' - signed 16-bit, Little-Endian)
                packed_sample = struct.pack('<h', sample_value)
                wav_file.writeframesraw(packed_sample)
                
    # Рассчитываем примерное время звучания
    duration = len(bits) / BAUD_RATE
    print(f"🚀 Готово! Аудиофайл успешно сохранен.")
    print(f"⏱ Время звучания файла: {duration:.1f} секунд.")

# ==========================================
# ПРИМЕР ИСПОЛЬЗОВАНИЯ
# ==========================================
if __name__ == "__main__":
    # 1. Создадим тестовый текстовый файл для передачи (если его нет)
    test_file = "hru.txt"
    with open(test_file, "wb") as f:
        f.write(b"Hello, Acoustic World!")
            
    # 2. Конвертируем файл в биты
    bits_to_transmit = encode_file_to_bits(test_file)
    
    # 3. Генерируем .wav файл
    generate_wav_from_bits(bits_to_transmit, "modem_sound.wav")