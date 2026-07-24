import zstandard as zstd
import sys
import os

def compress_file(input_path: str, level: int = 3):

    
    # Настройка сжатия
    compressor = zstd.ZstdCompressor(level=level)
    
    # Читаем исходный файл
    with open(input_path, 'rb') as f:
        data = f.read()
    
    # Сжимаем
    compressed = compressor.compress(data)
    
    # Сохраняем
    with open(r"src\data\send.txt", 'wb') as f:
        f.write(compressed)
    
    # Статистика
    original_size = os.path.getsize(input_path)
    compressed_size = len(compressed)
    ratio = (1 - compressed_size / original_size) * 100
    
    print(f"✅ Файл сжат:")
    print(f"   Исходный: {original_size:,} байт")
    print(f"   Сжатый:  {compressed_size:,} байт")
    print(f"   Экономия: {ratio:.1f}%")
    print(f"   Сохранён: {output_path}")
    
    return output_path


def decompress_file(input_path: str, output_path: str = None):
    """
    Распаковать файл .zst
    
    Args:
        input_path: путь к сжатому файлу
        output_path: путь к распакованному файлу (если None, убирает .zst)
    """
    if output_path is None:
        if input_path.endswith('.zst'):
            output_path = input_path[:-4]
        else:
            output_path = input_path + '.decompressed'
    
    # Настройка распаковки
    decompressor = zstd.ZstdDecompressor()
    
    # Читаем сжатый файл
    with open(input_path, 'rb') as f:
        compressed = f.read()
    
    # Распаковываем
    decompressed = decompressor.decompress(compressed)
    
    # Сохраняем
    with open(output_path, 'wb') as f:
        f.write(decompressed)
    
    print(f"✅ Файл распакован: {output_path}")
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование:")
        print("  Сжатие:   python script.py compress <файл> [уровень]")
        print("  Распаковка: python script.py decompress <файл.zst>")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "compress" and len(sys.argv) >= 3:
        level = int(sys.argv[3]) if len(sys.argv) > 3 else 3
        compress_file(sys.argv[2], level=level)
    
    elif command == "decompress" and len(sys.argv) >= 3:
        decompress_file(sys.argv[2])
    
    else:
        print("Неверная команда")