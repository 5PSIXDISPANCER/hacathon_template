# 1. поиск по расширениям файлов
# 2. преобразование полного пути и относительного
# 3. чтение файлов
# 4. запись файлов
import os


def write_config(config):
    config_path = r"src\data\config.py"
    try:
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("CONFIG = {\n")
            f.write(f"    'File': '{config['File']}',\n")
            f.write(f"    'Path': r'{config['Path']}',\n")
            f.write(f"    'Format': '{config['Format']}',\n")
            f.write(f"    'Freq': {config['Freq']},\n")
            f.write(f"    'Frame': {config['Frame']}\n")
            f.write("}\n")
    except Exception as e:
        print(f"Ошибка в записи конфига: {e}")


def bytes_file(path):
    """Читает файл целиком и возвращает его содержимое как bytes."""
    with open(path, "rb") as f:
        return f.read()


def write_bytes(data: bytes, path: str = r"src\data\Transmitter\received.7z"):
    """
    Записывает бинарные данные (например, принятый и собранный из
    чанков архив) в файл. Перезаписывает файл целиком (не дописывает),
    т.к. это одна принятая передача, а не лог.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    return path
