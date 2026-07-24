import customtkinter as CTk

def button_callback():
    print("button pressed")

app = CTk.CTk()
app.title("my app")
app.geometry("500x500")

button = CTk.CTkButton(app, text="my button", command=button_callback)
button.grid(row=0, column=0, padx=20, pady=20)

app.mainloop()