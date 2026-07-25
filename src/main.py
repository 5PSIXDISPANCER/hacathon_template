import queue
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
import os

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
        Фоновый прием аудио через sd.InputStream БЕЗ разрывов и ограничений по времени.
        Данные поступают в callback и накопляются в очереди, пока не взведен flag.
        """
        print("Прием и запись сигнала запущены (без разрывов)...")
        
        fs = 44100
        q = queue.Queue()

        # Callback вызывают фоновые драйверы аудиокарты без паузы
        def audio_callback(indata, frames, time_info, status):
            if status:
                print(f"[*] Статус аудиопотока: {status}")
            q.put(indata.copy())

        recorded_chunks = []

        # 1. Открываем непрерывный поток записи в формате int16
        with sd.InputStream(samplerate=fs, channels=1, dtype='int16', callback=audio_callback):
            # Поток пишет сам в фоновом режиме, пока мы ждем установки флага
            while not flag.is_set():
                time.sleep(0.05)
                # Вынимаем накопленные кусочки из очереди в наш список
                while not q.empty():
                    recorded_chunks.append(q.get())

            # Выбираем остатки из очереди после нажатия кнопки "Назад"
            while not q.empty():
                recorded_chunks.append(q.get())

        print("Прием остановлен пользователем. Обработка данных...")

        if recorded_chunks:
            # Склеиваем все куски в один монолитный массив
            full_audio = np.concatenate(recorded_chunks, axis=0).flatten()
            
            # Сохраняем WAV фал
            wav_dir = r"src\data\Wave\accept"
            os.makedirs(wav_dir, exist_ok=True)
            wav_path = os.path.join(wav_dir, "accepted.wav")
            
            wavfile.write(wav_path, fs, full_audio)
            print(f"Полный сигнал собран: {len(full_audio)} сэмплов ({len(full_audio)/fs:.2f} сек).")
            
            # ДЕКОДИРОВАНИЕ
            md = Modem()
            output_archive_path = r"src\data\res\received_archive.7z"
            
            # Передаем полный массив int16 напрямую в модем
            md.decode_large_file_from_samples(
                samples=full_audio,
                output_file_path=output_archive_path
            )
            print("Декодирование успешно завершено!")
        else:
            print("Запись оказалась пустой.")
        

    



        
if __name__ == "__main__":
    app = App()
    app.mainloop()