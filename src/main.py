
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

    def accept(self,flag):
        """
        Фоновое накопление аудио-данных до тех пор, пока не взведен flag
        """
        
        fs = 44100  # Частота дискретизации (измените на вашу FS, если нужно)
        chunk_duration = 0.1  # Проверяем флаг каждые 100 миллисекунд
        chunk_samples = int(fs * chunk_duration)
        
        recorded_chunks = []
        
        # Открываем поток ввода (микрофон)
        with sd.InputStream(samplerate=fs, channels=1, dtype='float32') as stream:
            while not flag.is_set():
                # Читаем кусочек звука из микрофона
                data, overflowed = stream.read(chunk_samples)
                recorded_chunks.append(data)
                
        # Объединяем все кусочки в один массив numpy
        if recorded_chunks:
            full_audio = np.concatenate(recorded_chunks, axis=0)
            
            # Сохраняем в wav-файл
            wavfile.write(fr"src\data\Wave\accept\accepted.wav", fs, full_audio)
        
        

    



        
if __name__ == "__main__":
    app = App()
    app.mainloop()