import os
import time
import py7zr

class Compressor():
    def __init__(self):
        pass

    def compress(self, source_path: str, output_archive_path=None):
        """
        Максимальное сжатие для файлов и папок размером до 10 МБ.
        Файлы меньше 10 кб - BZIP2
        Остальные - LZMA2

        Возвращает путь к созданному архиву (str) при успехе, либо None при ошибке.
        """
        if not os.path.exists(source_path):
            print(f"Ошибка: Путь '{source_path}' не существует.")
            return None

        # Автоматическое имя архива
        if not output_archive_path:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            target_dir = os.path.abspath(os.path.join(current_dir, "..", "..", "data", "Compressor"))
            os.makedirs(target_dir, exist_ok=True)
            pure_filename = os.path.basename(source_path)
            output_archive_path = os.path.join(target_dir, f"{pure_filename}.7z")

        # Конфигурация экстремального сжатия для малых объемов данных
        orig_size = self.get_size(source_path)
        
        if orig_size == 0:
            filters = [{'id': py7zr.FILTER_COPY}]
        elif orig_size < 10240:  # Если файл меньше 10 КБ
            filters = [{'id': py7zr.FILTER_BZIP2}]
        else:
            # ИСПРАВЛЕНО: 'dict' изменен на 'dict_size', а 'fb' на 'nice_len' (требование Python lzma)
            filters = [
                {
                    'id': py7zr.FILTER_LZMA2,
                    'dict_size': 16 * 1024 * 1024,  # 16 МБ словаря полностью перекрывают 10 МБ файла
                    'nice_len': 273,               # Максимальное количество проверяемых байт (Fast Byte)
                    'lc': 3,                       # Литеральные контекстные биты
                    'lp': 0,
                    'pb': 2
                }
            ]

        start_time = time.time()

        try:
            # Удаляем старый файл, если он существует, чтобы не ломать заголовки py7zr
            if os.path.exists(output_archive_path):
                os.remove(output_archive_path)

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
            print(f"Сжато за {elapsed_time:.2f}с, {orig_size} -> {arch_size} байт ({ratio:.1f}%)")

            return output_archive_path

        except Exception as e:
            print(f"\nОшибка при сжатии: {e}")
            return None

    def decompress(self, archive_path: str, output_dir: str = None):
        """
        Разархивирует файлы в отдельную папку.

        Возвращает путь к папке с распакованными файлами при успехе, либо None при ошибке.
        """
        if not os.path.exists(archive_path):
            print(f"Ошибка: Архив '{archive_path}' не найден.")
            return None

        if not os.path.isfile(archive_path):
            print(f"Ошибка: Путь '{archive_path}' не является файлом.")
            return None

        if not output_dir:
            base_name = os.path.splitext(os.path.basename(archive_path))[0]
            parent_dir = os.path.dirname(os.path.abspath(archive_path))
            output_dir = os.path.join(parent_dir, f"{base_name}_extracted")

        start_time = time.time()

        try:
            with py7zr.SevenZipFile(archive_path, mode='r') as archive:
                archive.extractall(path=output_dir)

            elapsed_time = time.time() - start_time
            print(f"Распаковано за {elapsed_time:.2f}с в '{output_dir}'")
            return output_dir

        except Exception as e:
            print(f"\nОшибка при декомпрессии: {e}")
            return None

    def get_size(self, path: str):
        """
        Выдает общий размер файла или папки
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
    compressor = Compressor()
    
    source_file = os.path.join("docs", "PROTOCOL.md")
    
    # Создаем тестовый файл больше 10 КБ, чтобы отработал именно блок LZMA2
    if not os.path.exists(source_file):
        os.makedirs("docs", exist_ok=True)
        with open(source_file, "w", encoding="utf-8") as f:
            f.write("Тестовые данные для проверки ультра-сжатия LZMA2 через py7zr. " * 300)
    
    do = compressor.get_size(source_file)
    
    # Передаем управление и получаем точный путь к созданному файлу
    archive_path = compressor.compress(source_file)
    
    if archive_path:
        posle = compressor.get_size(archive_path)
        print(f"До {do} байт, после {posle} байт")
        
        # Проверка декомпрессии (опционально)
        # compressor.decompress(archive_path)
    else:
        print("Сжатие не удалось.")