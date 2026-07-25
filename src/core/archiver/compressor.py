import os
import time
import py7zr


class Compressor():
    def __init__(self):
        pass

    def compress(self,source_path: str, output_archive_path  = None ):
        """
        Максимальное сжатие для файлов и папок размером до 10 МБ.
        Файлы меньше 10 кб - BZIP2
        Остальные - LZMA2
        """
        if not os.path.exists(source_path):
            print(f"Ошибка: Путь '{source_path}' не существует.")
            return

        # Автоматическое имя архива
        if not output_archive_path:
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    target_dir = os.path.abspath(os.path.join(current_dir, "..", "..", "data"))
                    os.makedirs(target_dir, exist_ok=True)
                    pure_filename = os.path.basename(source_path)
                    output_archive_path = os.path.join(target_dir, f"{pure_filename}.7z")
        # if not output_archive_path:
        #     base_name = os.path.basename(os.path.normpath(source_path))
        #     output_archive_path = f"{base_name}_max.7z"

        # Конфигурация экстремального сжатия для малых объемов данных
        orig_size = self.get_size(source_path)
        if orig_size == 0:
            filters = None
        elif orig_size < 10240:  # Если файл меньше 10 КБ (как ваш PROTOCOL.md)
            # Для микро-файлов BZIP2 в py7zr сжимает эффективнее и никогда не ломает заголовки
            filters = [{'id': py7zr.FILTER_BZIP2}]
        else:
            filters = [
                {
                    'id': py7zr.FILTER_LZMA2,
                    'dict': 16 * 1024 * 1024,     # 16 МБ словаря полностью перекрывают ваши 10 МБ файла
                    'fb': 273,                    # Максимальное количество проверяемых байт (Fast Byte)
                    'lc': 3,                      # Литеральные контекстные биты (стандарт для ультра)
                    'lp': 0,
                    'pb': 2
                }
            ]

        start_time = time.time()

        try:
            # Включаем solid-режим (непрерывный архив) для максимальной склейки мелких файлов
            with py7zr.SevenZipFile(output_archive_path, 'w', filters=filters) as archive:
                if os.path.isfile(source_path):
                    archive.write(source_path, os.path.basename(source_path))
                elif os.path.isdir(source_path):
                    archive.writeall(source_path, os.path.basename(os.path.normpath(source_path)))
            
            elapsed_time = time.time() - start_time
            orig_size = self.get_size(source_path)
            arch_size = os.path.getsize(output_archive_path)
            ratio = (arch_size / orig_size) * 100 if orig_size > 0 else 0

        except Exception as e:
            print(f"\n Ошибка при сжатии: {e}")

    def decompress(self, archive_path: str, output_dir: str =None):
        """
        Разархивирует файлы в отдельную папку
        """
        if not os.path.exists(archive_path):
            print(f"Ошибка: Архив '{archive_path}' не найден.")
            return

        if not os.path.isfile(archive_path):
            print(f"Ошибка: Путь '{archive_path}' не является файлом.")
            return

        # Если папка для распаковки не указаны, создаем ее рядом с архивом
        if not output_dir:
            # Убираем расширение .7z для имени папки
            base_name = os.path.splitext(os.path.basename(archive_path))[0]
            parent_dir = os.path.dirname(os.path.abspath(archive_path))
            output_dir = os.path.join(parent_dir, f"{base_name}_extracted")

        start_time = time.time()

        try:
            # Режим 'r' (read) автоматически считывает все LZMA2 фильтры из заголовка
            with py7zr.SevenZipFile(archive_path, mode='r') as archive:
                archive.extractall(path=output_dir)

        except Exception as e:
            print(f"\nОшибка при декомпрессии: {e}")

    def get_size(self,path: str):
        """
        Выдает размер файла
        """
        if os.path.isfile(path):
            return os.path.getsize(path)
        total_size = 0
        for dirpath, _, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.exists(fp):
                    total_size += os.path.getsize(fp)
        return total_size
    
    

if __name__ == "__main__":
    comressor = Compressor()
    do = comressor.get_size("docs\PROTOCOL.md")
    comressor.compress("docs\PROTOCOL.md")
    posle = comressor.get_size("PROTOCOL.md_max.7z")
    print(f"До {do}, после {posle}")
