
from core.gui.ui import App 
from core.archiver.compressor import Compressor
from data import config
import sys
class Main(App):
    def __init__(self):
        super().__init__()
    @staticmethod
    def operated_config():
            comperss_intil = Compressor()
            comperss_intil.compress(source_path=config.CONFIG['File'])

    def get_config(config):
        config_path = r"src\data\config.py"
        try:
            with open(config_path, "w", encoding="utf-8") as f:

                f.write("CONFIG = {\n")
                
                # Записываем строки. Символ r перед одинарными кавычками r'{...}' 
                # защитит пути к файлу от случайного экранирования (например, \n или \t в путях Windows)
                f.write(f"    'File': r'{config['File']}',\n")
                f.write(f"    'Format': '{config['Format']}',\n")
                f.write(f"    'Freq': {config['Freq']},\n")
                f.write(f"    'Frame': {config['Frame']}\n")
                
                # Закрываем словарь
                f.write("}\n")
        except Exception as e:
            print(f"Ошибка в записи")
        Main.operated_config()
    



        
if __name__ == "__main__":
    app = App()
    app.mainloop()