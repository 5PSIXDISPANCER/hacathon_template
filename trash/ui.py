import customtkinter as ctk
from tkinter import filedialog

# Настройка темы
ctk.set_appearance_mode("System")  # Варианты: "System", "Dark", "Light"
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Передача и приём файлов")
        self.geometry("500x580")
        self.resizable(False, False)

        # Переменные для хранения выбранных настроек
        self.selected_format = ctk.StringVar(value="jpg")
        self.selected_freq = ctk.StringVar(value="44100")
        self.selected_frame = ctk.StringVar(value="1024")
        self.file_path = ctk.StringVar(value="")

        # Главный контейнер для сцен
        self.main_container = ctk.CTkFrame(self)
        self.main_container.pack(fill="both", expand=True, padx=20, pady=20)

        # Запуск с главного меню
        self.show_main_menu()

    def clear_container(self):
        """Очистка контейнера перед отображением нового меню"""
        for widget in self.main_container.winfo_children():
            widget.destroy()

    # ================= 1. Главное меню =================
    def show_main_menu(self):
        self.clear_container()

        title = ctk.CTkLabel(
            self.main_container, 
            text="Главное меню", 
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title.pack(pady=(40, 30))

        btn_send = ctk.CTkButton(
            self.main_container, 
            text="Отправить", 
            font=ctk.CTkFont(size=16),
            height=45,
            command=self.show_send_menu
        )
        btn_send.pack(pady=15, fill="x", padx=50)

        btn_receive = ctk.CTkButton(
            self.main_container, 
            text="Принимать", 
            font=ctk.CTkFont(size=16),
            height=45,
            fg_color="#2b8a3e",
            hover_color="#237032",
            command=self.show_receive_menu
        )
        btn_receive.pack(pady=15, fill="x", padx=50)

    # ================= 2. Меню отправки =================
    def show_send_menu(self):
        self.clear_container()

        title = ctk.CTkLabel(
            self.main_container, 
            text="Параметры отправки", 
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title.pack(pady=(10, 15))

        # Блок 1: Формат файла
        lbl_format = ctk.CTkLabel(self.main_container, text="1. Формат файла:", font=ctk.CTkFont(weight="bold"))
        lbl_format.pack(anchor="w", padx=10, pady=(5, 2))
        
        seg_format = ctk.CTkSegmentedButton(
            self.main_container, 
            values=["jpg", "txt"], 
            variable=self.selected_format,
            command=lambda _: self.validate_form()
        )
        seg_format.pack(fill="x", padx=10, pady=(0, 10))

        # Блок 2: Частота
        lbl_freq = ctk.CTkLabel(self.main_container, text="2. Частота (Гц):", font=ctk.CTkFont(weight="bold"))
        lbl_freq.pack(anchor="w", padx=10, pady=(5, 2))
        
        seg_freq = ctk.CTkSegmentedButton(
            self.main_container, 
            values=["44100", "48000", "16000", "24000"], 
            variable=self.selected_freq,
            command=lambda _: self.validate_form()
        )
        seg_freq.pack(fill="x", padx=10, pady=(0, 10))

        # Блок 3: Размер фрейма
        lbl_frame = ctk.CTkLabel(self.main_container, text="3. Размер фрейма:", font=ctk.CTkFont(weight="bold"))
        lbl_frame.pack(anchor="w", padx=10, pady=(5, 2))
        
        seg_frame = ctk.CTkSegmentedButton(
            self.main_container, 
            values=["512", "1024", "2048", "4096"], 
            variable=self.selected_frame,
            command=lambda _: self.validate_form()
        )
        seg_frame.pack(fill="x", padx=10, pady=(0, 15))

        # Кнопка выбора файла и статусный текст
        btn_select_file = ctk.CTkButton(
            self.main_container, 
            text="Выбрать файл в проводнике", 
            command=self.select_file
        )
        btn_select_file.pack(pady=5)

        self.lbl_file_path = ctk.CTkLabel(
            self.main_container, 
            text="Файл не выбран", 
            font=ctk.CTkFont(size=11), 
            text_color="gray"
        )
        self.lbl_file_path.pack(pady=(0, 15))

        # Кнопка Отправить (изначально заблокирована)
        self.btn_submit = ctk.CTkButton(
            self.main_container, 
            text="Отправить", 
            state="disabled", 
            height=40,
            font=ctk.CTkFont(weight="bold"),
            command=self.show_progress_menu
        )
        self.btn_submit.pack(fill="x", padx=20, pady=5)

        # Кнопка «Назад»
        btn_back = ctk.CTkButton(
            self.main_container, 
            text="← Назад", 
            fg_color="transparent", 
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            command=self.show_main_menu
        )
        btn_back.pack(pady=5)

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
            self.lbl_file_path.configure(text=short_name, text_color=("black", "white"))
        
        self.validate_form()

    def validate_form(self):
        """Проверка выполнения всех условий для активации кнопки Отправить"""
        if (self.file_path.get() and 
            self.selected_format.get() and 
            self.selected_freq.get() and 
            self.selected_frame.get()):
            self.btn_submit.configure(state="normal")
        else:
            self.btn_submit.configure(state="disabled")

    # ================= 3. Меню прогресса =================
    def show_progress_menu(self):
        self.clear_container()

        title = ctk.CTkLabel(
            self.main_container, 
            text="Отправка файла", 
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title.pack(pady=(30, 15))

        # Отображение выбранных параметров
        file_name = self.file_path.get().split('/')[-1]
        info_text = (
            f"Файл: {file_name}\n"
            f"Формат: {self.selected_format.get()}\n"
            f"Частота: {self.selected_freq.get()} Гц\n"
            f"Размер фрейма: {self.selected_frame.get()}"
        )
        lbl_info = ctk.CTkLabel(
            self.main_container, 
            text=info_text, 
            justify="left", 
            font=ctk.CTkFont(size=13)
        )
        lbl_info.pack(pady=10)

        # Прогрессбар
        self.progressbar = ctk.CTkProgressBar(self.main_container, width=300)
        self.progressbar.pack(pady=30)
        self.progressbar.set(0)
        self.progressbar.start()  # Запуск циклической анимации

        btn_back = ctk.CTkButton(
            self.main_container, 
            text="Главное меню", 
            command=self.show_main_menu
        )
        btn_back.pack(pady=20)

    # ================= 4. Меню приёма =================
    def show_receive_menu(self):
        self.clear_container()

        title = ctk.CTkLabel(
            self.main_container, 
            text="Режим приёма", 
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title.pack(pady=(40, 20))

        # Карточка статуса
        status_card = ctk.CTkFrame(self.main_container, fg_color=("gray85", "gray20"))
        status_card.pack(fill="x", padx=20, pady=20)

        lbl_status = ctk.CTkLabel(
            status_card, 
            text="Идёт приём файла, включен микрофон", 
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#2b8a3e",
            wraplength=300
        )
        lbl_status.pack(pady=(30, 15), padx=20)

        # Индикатор активности микрофона/приёма
        progressbar = ctk.CTkProgressBar(status_card, width=220, mode="indeterminate")
        progressbar.pack(pady=(0, 25))
        progressbar.start()

        btn_back = ctk.CTkButton(
            self.main_container, 
            text="← Назад в меню", 
            command=self.show_main_menu
        )
        btn_back.pack(pady=20)


if __name__ == "__main__":
    app = App()
    app.mainloop()