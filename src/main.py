
from core.gui.ui import App 
from core.archiver.compressor import Compressor
from core.audio.receiver import Stream
from core.ggwave import converter
from core import utils
from core.audio.transmitter import listen
from core.audio.modem import Modem
import scipy.signal
from scipy.io import wavfile
import reedsolo
import sounddevice as sd
import time
import numpy as np

FS = 44100

class Main(App):
    def __init__(self):
        super().__init__()
    # @staticmethod
    # def send():
    #     search_pattern = os.path.join(r"src\data", "*.txt")
    #     found_files = glob.glob(search_pattern)
    #     with open(found_files[0], "rb") as f:
    #         file_bytes = f.read()
    #     Stream(waveform=file_bytes, rate = config.CONFIG['Freq'], frames_per_buffer=config.CONFIG["Frame"])
        

    # @staticmethod
    # def use_ggwave():
        
        
    #     search_pattern = os.path.join(r"src\data", "*.7z")
    #     found_files = glob.glob(search_pattern)
    #     with open(r"src\data\ggwavefile.txt", "wb") as f:
    #         f.write(converter.rad(found_files[0]))
    #     Main.send()

        

         
    # @staticmethod
    # def operated_config():
    #         comperss_intil = Compressor()
    #         comperss_intil.compress(source_path=config.CONFIG['File'])
    #         Main.use_ggwave()

    # def get_config(config):
      
    #     Main.operated_config()

    def send(dt,flag):
        if flag.is_set():
            return
        utils.write_config(config=dt)
        compressor_instance = Compressor() 
        compressor_instance.compress(source_path=dt["Path"])
        if flag.is_set():
            return
        md = Modem()
        file_size = md.encode_large_file(fr"src\data\Compressor\{dt["File"]}.7z",fr"src\data\Wave\send\{dt["File"]}.wav")
        wav_path = fr"src\data\Wave\send\{dt["File"]}.wav"
        if file_size > 0:
            _, tx_signal = wavfile.read(wav_path)
            
            # ВАЖНО: Меняем blocking=True на blocking=False, иначе мы не сможем
            # прервать воспроизведение звука, пока он полностью не доиграет!
            sd.play(tx_signal, samplerate=FS, blocking=False)
            
            # Рассчитываем длительность аудио в секундах
            duration = len(tx_signal) / FS
            start_time = time.time()
            
            # Запускаем цикл ожидания окончания звука с постоянной проверкой флага
            while time.time() - start_time < duration:
                if flag.is_set():
                    sd.stop() # Экстренно выключаем звук в динамиках/наушниках
                    return
                time.sleep(0.1) # Спим 100 мс, чтобы не нагружать процессор
                
            return

    def accept(flag):
        """
        Фоновый прием аудио через sd.rec БЕЗ ограничений по времени.
        Запись идет циклическими блоками до тех пор, пока не взведен flag.
        """
        print("Прием и запись сигнала запущены (время не ограничено)...")
        
        fs = 44100  # Настройте под вашу частоту дискретизации (FS)
        block_duration = 10  # Длина одного блока в секундах
        block_samples = int(block_duration * fs)
        
        recorded_blocks = []  # Здесь будем копить готовые блоки данных
        
        # 1. Запускаем запись самого первого блока
        current_record = sd.rec(
            frames=block_samples, 
            samplerate=fs, 
            channels=1, 
            dtype='float32', 
            blocking=False
        )
        
        block_start_time = time.time()
        
        # Основной цикл записи — работает бесконечно, пока не сработает flag
        while not flag.is_set():
            time.sleep(0.1)  # Проверяем кнопку каждые 100 мс
            
            elapsed_in_block = time.time() - block_start_time
            
            # Если текущий 10-секундный блок заполнился, а стоп не нажат
            if elapsed_in_block >= block_duration:
                # Сохраняем весь текущий блок целиком
                recorded_blocks.append(current_record)
                
                # Сразу же запускаем запись следующего блока без остановки девайса
                current_record = sd.rec(
                    frames=block_samples, 
                    samplerate=fs, 
                    channels=1, 
                    dtype='float32', 
                    blocking=False
                )
                block_start_time = time.time()
                print("Запись продолжается, выделен новый блок памяти...")

        # --- СЮДА МЫ ПОПАДАЕМ, КОГДА НАЖАТА КНОПКА "НАЗАД" (flag.is_set()) ---
        sd.stop()  # На всякий случай останавливаем аудиокарту
        print("Прием остановлен пользователем. Обработка данных...")
        
        # Вычисляем, сколько секунд/сэмплов успело записаться в ПОСЛЕДНЕМ незавершенном блоке
        final_elapsed = time.time() - block_start_time
        actual_samples_in_final = int(final_elapsed * fs)
        
        # Отрезаем тишину у последнего куска
        final_piece = current_record[:actual_samples_in_final]
        
        # Добавляем этот финальный кусочек к остальным сохраненным блокам
        recorded_blocks.append(final_piece)
        
        # Склеиваем все 10-секундные блоки и финальный кусок в один монолитный массив numpy
        full_audio = np.concatenate(recorded_blocks, axis=0)
        full_audio = full_audio.flatten()
        # Проверяем, что массив не пустой, и отправляем в модем
        if len(full_audio) > 0:
            wav_path = fr"src\data\Wave\accept\accepted.wav"
            wavfile.write(wav_path, fs, full_audio)
            print(f"Полный сигнал успешно собран. Длина массива: {len(full_audio)} сэмплов.")
            
            # ДЕКОДИРОВАНИЕ
            md = Modem()
            output_archive_path = fr"src\data\res\received_archive.7z"
            
            md.decode_large_file_from_samples(
                samples=full_audio,
                output_file_path=output_archive_path,
            )
            print("Декодирование успешно завершено!")
        else:
            print("Запись оказалась пустой.")     
        

    



        
if __name__ == "__main__":
    app = App()
    app.mainloop()