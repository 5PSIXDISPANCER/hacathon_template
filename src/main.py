
from core.gui.ui import App 
from core.archiver.compressor import Compressor
import os
import glob
from core.audio.receiver import Stream
from core.ggwave import converter
from core import utils
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

    def get_config(config):
      
        Main.operated_config()

    def send(dt):
        utils.write_config(config=dt)
        compressor_instance = Compressor() 
        compressor_instance.compress(source_path=dt["Path"])
        bytes = utils.bytes_file(fr"src\data\Compressor\{dt["File"]}.7z")
        wave = converter.encoded(bytes)
        Stream(waveform=wave, rate=int(dt["Freq"]), frames_per_buffer=int(dt["Frame"]))

        

    



        
if __name__ == "__main__":
    app = App()
    app.mainloop()