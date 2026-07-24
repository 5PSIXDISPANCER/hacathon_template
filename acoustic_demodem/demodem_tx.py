import numpy as np
import sounddevice as sd
import struct
from reedsolo import RSCodec, ReedSolomonError
import binascii

SAMPLE_RATE = 44100
BAUD_RATE = 50
FREQ_0 = 2000.0
FREQ_1 = 4000.0
SAMPLES_PER_BIT = int(SAMPLE_RATE / BAUD_RATE)
RS = RSCodec(10)

def record_audio(duration):
    print(f"Слушаю эфир {duration} секунд...")
    recording = sd.rec(int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
    sd.wait()
    return recording.flatten()

def demodulate(audio_signal):
    print("Демодуляция сигнала...")
    bits = []
    
    # Упрощенная логика: скользим окном по аудио и смотрим, какая частота доминирует
    # (В реальном проекте здесь нужен детектор преамбулы для точной синхронизации)
    
    for i in range(0, len(audio_signal) - SAMPLES_PER_BIT, SAMPLES_PER_BIT):
        chunk = audio_signal[i:i+SAMPLES_PER_BIT]
        # Применяем FFT для нахождения пиковых частот
        fft_result = np.fft.rfft(chunk)
        fft_freqs = np.fft.rfftfreq(len(chunk), 1/SAMPLE_RATE)
        
        peak_freq = fft_freqs[np.argmax(np.abs(fft_result))]
        
        # Определение бита с допуском +- 200 Гц
        if abs(peak_freq - FREQ_1) < 200:
            bits.append(1)
        elif abs(peak_freq - FREQ_0) < 200:
            bits.append(0)
            
    return bits

def decode_and_save(bits, output_filename="received.txt"):
    # Перевод бит в байты
    byte_array = np.packbits(bits)
    
    try:
        # Извлечение заголовка (8 байт: 4 байта длина, 4 байта CRC)
        payload_len, expected_crc = struct.unpack('>II', byte_array[:8])
        encoded_data = byte_array[8:8+payload_len]
        
        # Коррекция ошибок
        decoded_data = RS.decode(encoded_data)[0]
        
        # Проверка целостности
        actual_crc = binascii.crc32(decoded_data) & 0xffffffff
        if actual_crc == expected_crc:
            with open(output_filename, 'wb') as f:
                f.write(decoded_data)
            print(f"Успех! Файл сохранен как {output_filename}. Целостность подтверждена.")
        else:
            print("Ошибка: CRC не совпадает. Файл поврежден.")
            
    except ReedSolomonError:
        print("Ошибка: Слишком много шума, FEC не смог восстановить данные.")
    except Exception as e:
        print(f"Ошибка парсинга данных: {e}")

# Пример запуска (нужно указать примерное время передачи)
# audio = record_audio(15)
# bits = demodulate(audio)
# decode_and_save(bits)