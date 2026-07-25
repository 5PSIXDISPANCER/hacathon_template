import os
import threading

from core.gui.ui import App
from core.archiver.compressor import Compressor
from core.audio.receiver import Stream
from core.ggwave import converter
from core import utils
from core.audio.transmitter import listen


class Main(App):
    def __init__(self):
        super().__init__()

    # ============ Хуки UI: запускают реальную логику в фоновых потоках ============
    # (чтобы Stream()/listen(), которые блокируют выполнение на время всей
    # передачи, не морозили окно tkinter)

    def start_transfer(self):
        dt = {
            "File": os.path.splitext(os.path.basename(self.file_path.get()))[0],
            "Path": self.file_path.get(),
            "Freq": self.selected_freq.get(),
            "Frame": self.selected_frame.get(),
        }
        threading.Thread(target=self._send_worker, args=(dt,), daemon=True).start()

    def _send_worker(self, dt):
        try:
            Main.send(dt)
            self.after(0, self._on_transfer_done, True, None)
        except Exception as e:
            self.after(0, self._on_transfer_done, False, str(e))

    def _on_transfer_done(self, success, error):
        # Виджеты могли уже быть уничтожены, если пользователь ушёл с экрана
        if not hasattr(self, "lbl_transfer_status") or not self.lbl_transfer_status.winfo_exists():
            return
        self.progressbar.stop()
        self.progressbar.set(1 if success else 0)
        if success:
            self.lbl_transfer_status.configure(text="Готово: файл передан", text_color="#2b8a3e")
        else:
            self.lbl_transfer_status.configure(text=f"Ошибка передачи: {error}", text_color="#c0392b")

    def start_receiving(self):
        threading.Thread(target=self._receive_worker, daemon=True).start()

    def _receive_worker(self):
        try:
            result_dir = Main.accept()
            self.after(0, self._on_receive_done, True, result_dir)
        except Exception as e:
            self.after(0, self._on_receive_done, False, str(e))

    def _on_receive_done(self, success, info):
        if not hasattr(self, "lbl_status") or not self.lbl_status.winfo_exists():
            return
        self.receive_progressbar.stop()
        if success:
            self.lbl_status.configure(
                text=f"Файл принят и распакован:\n{info}",
                text_color="#2b8a3e"
            )
        else:
            self.lbl_status.configure(text=f"Ошибка приёма: {info}", text_color="#c0392b")

    # ============ Собственно бизнес-логика ============

    @staticmethod
    def send(dt):
        """
        1. Сохраняет конфиг
        2. Сжимает выбранный файл в .7z
        3. Бьёт архив на чанки и кодирует каждый в ggwave-волну
        4. Проигрывает чанки по очереди через колонки
        """
        utils.write_config(config=dt)

        compressor_instance = Compressor()
        archive_path = compressor_instance.compress(source_path=dt["Path"])
        if not archive_path:
            raise RuntimeError("Не удалось сжать файл")

        archive_bytes = utils.bytes_file(archive_path)
        waveforms = converter.encode_file(archive_bytes, protocol_id=1, volume=20)

        Stream(waveforms, rate=int(dt["Freq"]), frames_per_buffer=int(dt["Frame"]))

    @staticmethod
    def accept():
        """
        1. Слушает микрофон и собирает чанки в единый .7z архив
        2. Сохраняет архив на диск
        3. Распаковывает его

        Возвращает путь к папке с распакованными файлами.
        Бросает исключение, если приём не удался.
        """
        archive_bytes = listen()
        if archive_bytes is None:
            raise RuntimeError("Не удалось принять ни одного чанка")

        archive_path = utils.write_bytes(
            data=archive_bytes,
            path=r"src\data\Transmitter\received.7z"
        )

        compressor_instance = Compressor()
        result_dir = compressor_instance.decompress(archive_path)
        if not result_dir:
            raise RuntimeError("Архив принят, но не удалось его распаковать (возможно, потеряны чанки)")

        return result_dir


if __name__ == "__main__":
    app = Main()
    app.mainloop()
