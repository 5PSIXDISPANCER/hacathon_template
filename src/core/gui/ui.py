import customtkinter as ctk
from tkinter import filedialog
import threading
from ..audio.receiver import Stream
import os
# Принудительно ставим темную тему, как в клиенте Dota 2
ctk.set_appearance_mode("Dark")

# Цветовая палитра Dota 2
DOTA_BG = "#181a1f"           # Темный фон клиента
DOTA_PANEL = "#21242c"        # Цвет панелей
DOTA_RED = "#8c1b12"          # Фирменный красный
DOTA_RED_HOVER = "#b73027"    # Красный при наведении
DOTA_GOLD = "#d29a43"         # Золотой текст/акценты
DOTA_ACCEPT = "#2ea664"       # Зеленый цвет кнопки "Игра найдена"
DOTA_ACCEPT_HOVER = "#39c077" # Зеленый при наведении


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Dota 2 File Transfer")
        self.geometry("500x580")
        self.resizable(False, False)
        # Устанавливаем цвет фона окна
        self.configure(fg_color=DOTA_BG)

        # Переменные для хранения выбранных настроек
        self.selected_format = ctk.StringVar(value="bin")
        self.selected_freq = ctk.StringVar(value="44100")
        self.selected_frame = ctk.StringVar(value="1024")
        self.file_path = ctk.StringVar(value="")

        # Главный контейнер для сцен
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
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
            text="ГЛАВНОЕ МЕНЮ", 
            font=ctk.CTkFont(family="Arial", size=26, weight="bold"),
            text_color=DOTA_GOLD
        )
        title.pack(pady=(60, 40))

        # Кнопка отправки (Dota Red)
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

        # Кнопка принятия (Match Found Green)
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

        # Блок 1: Формат файла
        lbl_format = ctk.CTkLabel(self.main_container, text="1. ФОРМАТ ФАЙЛА:", font=ctk.CTkFont(weight="bold", size=12), text_color="#a0a5b5")
        lbl_format.pack(anchor="w", padx=10, pady=(5, 2))
        
        seg_format = ctk.CTkSegmentedButton(
            self.main_container, 
            values=["bin", "txt"], 
            variable=self.selected_format,
            command=lambda _: self.validate_form(),
            **seg_kwargs
        )
        seg_format.pack(fill="x", padx=10, pady=(0, 10))

        # Блок 2: Частота
        lbl_freq = ctk.CTkLabel(self.main_container, text="2. ЧАСТОТА (ГЦ):", font=ctk.CTkFont(weight="bold", size=12), text_color="#a0a5b5")
        lbl_freq.pack(anchor="w", padx=10, pady=(5, 2))
        
        seg_freq = ctk.CTkSegmentedButton(
            self.main_container, 
            values=["16000", "24000", "44100", "48000"], 
            variable=self.selected_freq,
            command=lambda _: self.validate_form(),
            **seg_kwargs
        )
        seg_freq.pack(fill="x", padx=10, pady=(0, 10))

        # Блок 3: Размер фрейма
        lbl_frame = ctk.CTkLabel(self.main_container, text="3. РАЗМЕР ФРЕЙМА:", font=ctk.CTkFont(weight="bold", size=12), text_color="#a0a5b5")
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
            text_color="#767a85"
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
            fg_color=DOTA_RED,
            hover_color=DOTA_RED_HOVER,
            command=self.show_progress_menu
        )
        self.btn_submit.pack(fill="x", padx=20, pady=5)

        # Кнопка «Назад»
        btn_back = ctk.CTkButton(
            self.main_container, 
            text="← НАЗАД", 
            fg_color="transparent", 
            text_color="#767a85",
            hover_color=DOTA_PANEL,
            corner_radius=4,
            command=self.show_main_menu
        )
        btn_back.pack(pady=10)

        self.validate_form()

    def select_file(self):
        fmt = self.selected_format.get()
        filetypes = [(f"Файлы (*.{fmt})", f"*.{fmt}"), ("Все файлы", "*.*")]
        
        filename = filedialog.askopenfilename(
            title="Выберите файл", 
            filetypes=filetypes
        )
        
        if filename:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
            rel_path = os.path.relpath(filename, start=self.project_root)
            rel_path = rel_path.replace("\\", "/")
            
            self.file_path.set(filename)
            short_name = filename if len(filename) < 35 else "..." + filename[-32:]
            self.lbl_file_path.configure(text=short_name, text_color=DOTA_GOLD)
        
        self.validate_form()

    def validate_form(self):
        if (self.file_path.get() and 
            self.selected_format.get() and 
            self.selected_freq.get() and 
            self.selected_frame.get()):
            self.btn_submit.configure(state="normal", fg_color=DOTA_RED)
        else:
            self.btn_submit.configure(state="disabled", fg_color=DOTA_PANEL)

    # ================= 3. Меню прогресса =================
    def show_progress_menu(self):

        self.clear_container()

        config = {
            "File": self.file_path.get(), 
            "Format": self.selected_format.get().upper(),
            "Freq": self.selected_freq.get(), 
            "Frame": self.selected_frame.get()
        }

        self.send_config(config)




        

        title = ctk.CTkLabel(
            self.main_container, 
            text="ОТПРАВКА ФАЙЛА...", 
            font=ctk.CTkFont(family="Arial", size=22, weight="bold"),
            text_color=DOTA_GOLD
        )
        title.pack(pady=(40, 15))

        file_name = self.file_path.get().split('/')[-1]
        info_text = (
            f"ЦЕЛЬ: {self.file_path.get().split('/')[-1]}\n"
            f"ТИП ДАННЫХ: {config['Format']}\n"
            f"ЧАСТОТА КАНАЛА: {config['Freq']} Гц\n"
            f"РАЗМЕР ФРЕЙМА: {config['Frame']}"
        )
        lbl_info = ctk.CTkLabel(
            self.main_container, 
            text=info_text, 
            justify="center", 
            font=ctk.CTkFont(size=14),
            text_color="#a0a5b5"
        )
        lbl_info.pack(pady=20)

        # Прогрессбар (Золотой как Aegis)
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
        self.progressbar.start() 

        btn_back = ctk.CTkButton(
            self.main_container, 
            text="ОТМЕНИТЬ (НАЗАД)",
            font=ctk.CTkFont(weight="bold"),
            fg_color=DOTA_PANEL,
            hover_color="#343843",
            corner_radius=4,
            command=self.show_main_menu
        )
        btn_back.pack(pady=20)
        

    # ================= 4. Меню приёма =================
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

        # Стилизация текста под внутриигровой войсчат
        lbl_status = ctk.CTkLabel(
            status_card, 
            text="ИДЁТ ПРИЁМ ФАЙЛА...\nМИКРОФОН АКТИВЕН", 
            font=ctk.CTkFont(family="Arial", size=16, weight="bold"),
            text_color=DOTA_RED,
            wraplength=300
        )
        lbl_status.pack(pady=(30, 15), padx=20)

        # Индикатор (как каст способности)
        progressbar = ctk.CTkProgressBar(
            status_card, 
            width=250, 
            height=8,
            mode="indeterminate",
            progress_color=DOTA_RED,
            fg_color="#181a1f",
            corner_radius=0
        )
        progressbar.pack(pady=(0, 30))
        progressbar.start()

        btn_back = ctk.CTkButton(
            self.main_container, 
            text="ПОКИНУТЬ ЛОББИ (НАЗАД)",
            font=ctk.CTkFont(weight="bold"),
            fg_color="transparent", 
            text_color="#767a85",
            hover_color=DOTA_PANEL,
            corner_radius=4,
            command=self.show_main_menu
        )
        btn_back.pack(pady=20)

    def send_config(self, config):
        print("КЛИК СРАБОТАЛ!")
        import main
        print(config)
        thread = threading.Thread(
        
        target=main.Main.get_config, args=(config,),daemon=True)
        thread.start()






if __name__ == "__main__":
    app = App()
    app.mainloop()