import customtkinter as ctk
from tkinter import filedialog

# Настройка темы
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# ========== Цветовая палитра Dota 2 ==========
DOTA_BG = "#181a1f"
DOTA_PANEL = "#21242c"
DOTA_RED = "#8c1b12"
DOTA_RED_HOVER = "#b73027"
DOTA_GOLD = "#d29a43"
DOTA_ACCEPT = "#2ea664"
DOTA_ACCEPT_HOVER = "#39c077"
DOTA_TEXT_SECONDARY = "#a0a5b5"
DOTA_TEXT_MUTED = "#767a85"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Передача и приём файлов")
        self.geometry("500x580")
        self.resizable(False, False)
        self.configure(fg_color=DOTA_BG)      # тёмный фон окна

        # Переменные для хранения выбранных настроек
        self.selected_freq = ctk.StringVar(value="44100")
        self.selected_frame = ctk.StringVar(value="1024")
        self.file_path = ctk.StringVar(value="")

        # Главный контейнер для сцен (прозрачный, чтобы видеть фон окна)
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=20)

        # Запуск с главного меню
        self.show_main_menu()

    def clear_container(self):
        """Очистка контейнера перед отображением нового меню"""
        for widget in self.main_container.winfo_children():
            widget.destroy()

    # ============ Хуки для реальной логики (переопределяются в Main) ============
    def start_transfer(self):
        """
        Вызывается сразу после отрисовки экрана прогресса отправки.
        В базовом App ничего не делает (чистый UI-превью).
        """
        pass

    def start_receiving(self):
        """
        Вызывается сразу после отрисовки экрана приёма.
        В базовом App ничего не делает.
        """
        pass

    # ================= 1. Главное меню (Dota‑стиль) =================
    def show_main_menu(self):
        self.clear_container()

        title = ctk.CTkLabel(
            self.main_container,
            text="ГЛАВНОЕ МЕНЮ",
            font=ctk.CTkFont(family="Arial", size=26, weight="bold"),
            text_color=DOTA_GOLD
        )
        title.pack(pady=(60, 40))

        btn_send = ctk.CTkButton(
            self.main_container,
            text="ОТПРАВИТЬ",
            font=ctk.CTkFont(family="Arial", size=18, weight="bold"),
            height=55,
            corner_radius=4,
            fg_color=DOTA_RED,
            hover_color=DOTA_RED_HOVER,
            text_color="white",
            command=self.show_send_menu
        )
        btn_send.pack(pady=15, fill="x", padx=50)

        btn_receive = ctk.CTkButton(
            self.main_container,
            text="ПРИНИМАТЬ",
            font=ctk.CTkFont(family="Arial", size=18, weight="bold"),
            height=55,
            corner_radius=4,
            fg_color=DOTA_ACCEPT,
            hover_color=DOTA_ACCEPT_HOVER,
            text_color="white",
            command=self.show_receive_menu
        )
        btn_receive.pack(pady=15, fill="x", padx=50)

    # ================= 2. Меню отправки =================
    def show_send_menu(self):
        self.clear_container()

        title = ctk.CTkLabel(
            self.main_container,
            text="ПАРАМЕТРЫ ПЕРЕДАЧИ",
            font=ctk.CTkFont(family="Arial", size=20, weight="bold"),
            text_color=DOTA_GOLD
        )
        title.pack(pady=(0, 15))

        # Общие стили для сегментированных кнопок
        seg_kwargs = {
            "fg_color": DOTA_PANEL,
            "selected_color": DOTA_RED,
            "selected_hover_color": DOTA_RED_HOVER,
            "unselected_color": DOTA_PANEL,
            "unselected_hover_color": "#343843",
            "text_color": "white",
            "corner_radius": 4
        }

        # Блок 2: Частота
        lbl_freq = ctk.CTkLabel(
            self.main_container,
            text="1. ЧАСТОТА ДИСКРЕТЕЗАЦИИ (ГЦ) ВАШЕГО МИКРОФОНА :",
            font=ctk.CTkFont(weight="bold", size=12),
            text_color=DOTA_TEXT_SECONDARY
        )
        lbl_freq.pack(anchor="w", padx=10, pady=(5, 2))

        seg_freq = ctk.CTkSegmentedButton(
            self.main_container,
            values=["44100", "48000", "16000", "24000"],
            variable=self.selected_freq,
            command=lambda _: self.validate_form(),
            **seg_kwargs
        )
        seg_freq.pack(fill="x", padx=10, pady=(0, 10))

        # Блок 3: Размер фрейма
        lbl_frame = ctk.CTkLabel(
            self.main_container,
            text="2. РАЗМЕР ФРЕЙМА:",
            font=ctk.CTkFont(weight="bold", size=12),
            text_color=DOTA_TEXT_SECONDARY
        )
        lbl_frame.pack(anchor="w", padx=10, pady=(5, 2))

        seg_frame = ctk.CTkSegmentedButton(
            self.main_container,
            values=["512", "1024", "2048", "4096"],
            variable=self.selected_frame,
            command=lambda _: self.validate_form(),
            **seg_kwargs
        )
        seg_frame.pack(fill="x", padx=10, pady=(0, 15))

        # Кнопка выбора файла
        btn_select_file = ctk.CTkButton(
            self.main_container,
            text="ВЫБРАТЬ ФАЙЛ",
            font=ctk.CTkFont(weight="bold"),
            fg_color=DOTA_PANEL,
            hover_color="#343843",
            corner_radius=4,
            command=self.select_file
        )
        btn_select_file.pack(pady=5)

        self.lbl_file_path = ctk.CTkLabel(
            self.main_container,
            text="Файл не выбран",
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color=DOTA_TEXT_MUTED
        )
        self.lbl_file_path.pack(pady=(0, 15))

        # Кнопка Отправить (изначально заблокирована)
        self.btn_submit = ctk.CTkButton(
            self.main_container,
            text="ОТПРАВИТЬ",
            state="disabled",
            height=45,
            corner_radius=4,
            font=ctk.CTkFont(weight="bold", size=16),
            fg_color=DOTA_PANEL,          # неактивный цвет
            hover_color=DOTA_PANEL,
            command=self.show_progress_menu
        )
        self.btn_submit.pack(fill="x", padx=20, pady=5)

        # Кнопка «Назад»
        btn_back = ctk.CTkButton(
            self.main_container,
            text="← НАЗАД",
            fg_color="transparent",
            text_color=DOTA_TEXT_MUTED,
            hover_color=DOTA_PANEL,
            corner_radius=4,
            command=self.show_main_menu
        )
        btn_back.pack(pady=10)

        self.validate_form()

    def select_file(self):
        """Открытие системного проводника"""
        fmt = self.selected_format.get()
        filetypes = [(f"Файлы (*.{fmt})", f"*.{fmt}"), ("Все файлы", "*.*")]

        filename = filedialog.askopenfilename(
            title="Выберите файл",
            filetypes=filetypes
        )

        if filename:
            self.file_path.set(filename)
            short_name = filename if len(filename) < 35 else "..." + filename[-32:]
            self.lbl_file_path.configure(text=short_name, text_color=DOTA_GOLD)

        self.validate_form()

    def validate_form(self):
        """Проверка выполнения всех условий для активации кнопки Отправить"""
        if (self.file_path.get() and
            self.selected_freq.get() and
            self.selected_frame.get()):
            self.btn_submit.configure(state="normal", fg_color=DOTA_RED, hover_color=DOTA_RED_HOVER)
        else:
            self.btn_submit.configure(state="disabled", fg_color=DOTA_PANEL, hover_color=DOTA_PANEL)

    # ================= 3. Меню прогресса (Dota‑стиль) =================
    def show_progress_menu(self):
        self.clear_container()

        title = ctk.CTkLabel(
            self.main_container,
            text="ОТПРАВКА ФАЙЛА...",
            font=ctk.CTkFont(family="Arial", size=22, weight="bold"),
            text_color=DOTA_GOLD
        )
        title.pack(pady=(40, 15))

        file_name = self.file_path.get().split('/')[-1]
        info_text = (
            f"ЦЕЛЬ: {file_name}\n"
            f"ТИП ДАННЫХ: {self.selected_format.get().upper()}\n"
            f"ЧАСТОТА КАНАЛА: {self.selected_freq.get()} Гц\n"
            f"РАЗМЕР ФРЕЙМА: {self.selected_frame.get()}"
        )
        lbl_info = ctk.CTkLabel(
            self.main_container,
            text=info_text,
            justify="center",
            font=ctk.CTkFont(size=14),
            text_color=DOTA_TEXT_SECONDARY
        )
        lbl_info.pack(pady=20)

        # Прогрессбар (золотой, как Aegis)
        self.progressbar = ctk.CTkProgressBar(
            self.main_container,
            width=350,
            height=15,
            progress_color=DOTA_GOLD,
            fg_color=DOTA_PANEL,
            corner_radius=0
        )
        self.progressbar.pack(pady=30)
        self.progressbar.set(0)
        self.progressbar.start()   # циклическая анимация

        self.lbl_transfer_status = ctk.CTkLabel(
            self.main_container,
            text="Передача может занять продолжительное время — это нормально для передачи данных звуком.",
            font=ctk.CTkFont(size=12),
            text_color=DOTA_TEXT_MUTED,
            wraplength=380,
            justify="center"
        )
        self.lbl_transfer_status.pack(pady=(0, 10))

        btn_back = ctk.CTkButton(
            self.main_container,
            text="ГЛАВНОЕ МЕНЮ",
            font=ctk.CTkFont(weight="bold"),
            fg_color=DOTA_PANEL,
            hover_color="#343843",
            corner_radius=4,
            command=self.show_main_menu
        )
        btn_back.pack(pady=20)

        # Запуск реальной отправки (в базовом App — ничего)
        self.start_transfer()

    # ================= 4. Меню приёма (Dota‑стиль) =================
    def show_receive_menu(self):
        self.clear_container()

        title = ctk.CTkLabel(
            self.main_container,
            text="РЕЖИМ ПРИЁМА",
            font=ctk.CTkFont(family="Arial", size=22, weight="bold"),
            text_color=DOTA_GOLD
        )
        title.pack(pady=(40, 20))

        # Карточка статуса
        status_card = ctk.CTkFrame(self.main_container, fg_color=DOTA_PANEL, corner_radius=8)
        status_card.pack(fill="x", padx=20, pady=20)

        self.lbl_status = ctk.CTkLabel(
            status_card,
            text="Идёт приём файла, включен микрофон",
            font=ctk.CTkFont(family="Arial", size=15, weight="bold"),
            text_color=DOTA_ACCEPT,
            wraplength=300
        )
        self.lbl_status.pack(pady=(30, 15), padx=20)

        # Индикатор активности
        self.receive_progressbar = ctk.CTkProgressBar(
            status_card,
            width=250,
            height=8,
            mode="indeterminate",
            progress_color=DOTA_RED,
            fg_color="#181a1f",
            corner_radius=0
        )
        self.receive_progressbar.pack(pady=(0, 30))
        self.receive_progressbar.start()

        btn_back = ctk.CTkButton(
            self.main_container,
            text="← НАЗАД В МЕНЮ",
            fg_color="transparent",
            text_color=DOTA_TEXT_MUTED,
            hover_color=DOTA_PANEL,
            corner_radius=4,
            command=self.show_main_menu
        )
        btn_back.pack(pady=20)

        # Запуск реального прослушивания (в базовом App — ничего)
        self.start_receiving()


if __name__ == "__main__":
    app = App()
    app.mainloop()