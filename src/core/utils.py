# 1. поиск по расширениям файлов
# 2. преобразование полного пути и относительного
# 3. чтение файлов
# 4. запись файлов
import os 
import glob
def write_config(config):
    config_path = r"src\data\config.py"
    try:
                with open(config_path, "w", encoding="utf-8") as f:
                    f.write("CONFIG = {\n")
                    f.write(f"    'File': '{config['File']}',\n")
                    f.write(f"    'Path': r'{config['Path']}',\n")
                    f.write(f"    'Format': '{config['Format']}',\n")
                    f.write(f"    'Freq': {config['Freq']},\n")
                    f.write(f"    'Frame': {config['Frame']}\n")
                    f.write("}\n")
    except Exception as e:
            print(f"Ошибка в записи")

# def find_file(type):
#        search_pattern = os.path.join(r"src\data", f"*.{type}")
#        found_files = glob.glob(search_pattern)
#        read_file(path=found_files)

def bytes_file(path):
       b = open(fr"{path}","rb").read()
       return b

