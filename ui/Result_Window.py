import customtkinter as ctk
import tkinter as tk
import threading
import queue
import json
from datetime import datetime

class ResultWindow:
    def __init__(self, parent, config, interpreter):
        self.parent = parent
        self.config = config
        self.interpreter = interpreter
        self.queue = queue.Queue()
        self.window = None
        self.result_textbox = None
        self.input_entry = None
        self.execution_thread_active = False
        self.last_code = ""
        self.os_bar_visible = True  # controla a visibilidade da barra de título

    def create_window(self):
        if not self.window or not self.window.winfo_exists():
            self.window = ctk.CTkToplevel(self.parent)
            self.window.title("Nexus Shell")
            self.window.geometry("800x500")
            self.window.configure(fg_color=self.config["bg_color"])
            self.window.protocol("WM_DELETE_WINDOW", self.on_close)

            # Menu superior
            menubar = tk.Menu(self.window)
            settings_menu = tk.Menu(menubar, tearoff=0)
            settings_menu.add_command(label="Clean Shell", command=self.clear_console)
            settings_menu.add_command(label="Run Again", command=self.run_again)
            settings_menu.add_command(label="OS Bar", command=self.toggle_os_bar)
            settings_menu.add_command(label="7ETW", command=self.show_executions_history)
            menubar.add_cascade(label="Settings", menu=settings_menu)
            self.window.config(menu=menubar)

            # Área de texto para saída
            self.result_textbox = tk.Text(
                self.window,
                wrap="word",
                font=("JetBrains Mono", self.config["font_size"]),
                bg=self.config["bg_color"],
                fg=self.config["fg_color"],
                insertbackground=self.config["fg_color"],
                borderwidth=0,
                relief="flat",
                padx=10,
                pady=10
            )
            self.result_textbox.pack(expand=True, fill="both", padx=10, pady=(10, 5))
            self.result_textbox.configure(state="normal")
            self.result_textbox.insert(
                "1.0",
                "=============================== Nexus Shell ===============================\n===========================================================================\n"
            )
            self.result_textbox.configure(state="disabled")

            # Campo de entrada
            self.input_entry = ctk.CTkEntry(
                self.window,
                placeholder_text="Type your input here...",
                fg_color=self.config["panel_bg"],
                text_color=self.config["fg_color"],
                font=("JetBrains Mono", self.config["font_size"]),
                height=30,
                border_width=0
            )
            self.input_entry.pack(fill="x", padx=10, pady=(0, 10))
            self.input_entry.bind("<Return>", self.submit_input)
            self.input_entry.configure(state="disabled")

            self.setup_tags()

    def output_to_gui(self, text, is_error=False):
        def update():
            self.result_textbox.configure(state="normal")
            tag = "error" if is_error else None
            self.result_textbox.insert("end", text + "\n", tag)
            self.result_textbox.yview("end")
            self.result_textbox.configure(state="disabled")
        self.parent.after(0, update)

    def submit_input(self, event=None):
        if self.input_entry.cget("state") == "normal":
            text = self.input_entry.get().strip()
            self.input_entry.delete(0, "end")
            self.result_textbox.configure(state="normal")
            self.result_textbox.insert("end", f"{text}\n")
            self.result_textbox.configure(state="disabled")
            self.result_textbox.yview("end")
            self.input_entry.configure(state="disabled")
            self.queue.put(text)
            if hasattr(self, "input_ready_event"):
                self.input_ready_event.set()
            return "break"

    def shell_input(self, prompt=""):
        self.input_ready_event = threading.Event()
        def enable_input():
            self.result_textbox.configure(state="normal")
            self.result_textbox.insert("end", f"{prompt}", "prompt")
            self.result_textbox.configure(state="disabled")
            self.result_textbox.yview("end")
            self.input_entry.configure(state="normal")
            self.input_entry.focus_set()
            self.window.focus_force()
        self.parent.after(0, enable_input)
        self.input_ready_event.wait()
        return self.queue.get()

    def clear_console(self):
        if self.result_textbox:
            self.result_textbox.configure(state="normal")
            self.result_textbox.delete("1.0", "end")
            self.result_textbox.insert(
                "1.0",
                "=============================== Nexus Shell ===============================\n"
            )
            self.result_textbox.configure(state="disabled")

    def apply_theme(self, config):
        self.config = config
        if self.window and self.window.winfo_exists():
            self.window.configure(fg_color=config["bg_color"])
            self.result_textbox.configure(
                bg=config["bg_color"],
                fg=config["fg_color"],
                insertbackground=config["fg_color"],
                font=("JetBrains Mono", config["font_size"])
            )
            self.input_entry.configure(
                fg_color=config["panel_bg"],
                text_color=config["fg_color"],
                font=("JetBrains Mono", config["font_size"])
            )

    def on_close(self):
        if self.window:
            self.window.destroy()
        self.window = None
        self.result_textbox = None
        self.input_entry = None

    def execute_code(self, code):
        self.create_window()
        self.execution_thread_active = True
        self.last_code = code
        self.input_entry.configure(state="normal")
        self.input_entry.focus_set()

        # Salva execução
        self.save_execution(code)

        def execute():
            try:
                self.interpreter.variables.clear()
                self.interpreter.run_nexus_code(
                    code,
                    input_func=self.shell_input,
                    output_func=self.output_to_gui
                )
            except Exception as e:
                self.output_to_gui(f"[Execution Error] {str(e)}", is_error=True)
            finally:
                self.execution_thread_active = False

        threading.Thread(target=execute, daemon=True).start()

    def setup_tags(self):
        self.result_textbox.tag_configure("prompt", foreground="#4a9eff")
        self.result_textbox.tag_configure("error", foreground="#e06c75")

    def run_again(self):
        if self.last_code:
            self.execute_code(self.last_code)

    # ----------------- OS Bar --------------------
    def toggle_os_bar(self):
        self.os_bar_visible = not self.os_bar_visible
        self.window.overrideredirect(not self.os_bar_visible)
        if not self.os_bar_visible:
            self.create_custom_titlebar()
        else:
            if hasattr(self, "custom_titlebar"):
                self.custom_titlebar.destroy()

    def create_custom_titlebar(self):
        if hasattr(self, "custom_titlebar") and self.custom_titlebar.winfo_exists():
            return

        self.custom_titlebar = ctk.CTkFrame(self.window, height=30, fg_color="#2b2b2b")
        self.custom_titlebar.pack(fill="x", side="top")

        self.title_label = ctk.CTkLabel(self.custom_titlebar, text=self.window.title(), fg_color="#2b2b2b")
        self.title_label.pack(side="left", padx=10)

        self.close_btn = ctk.CTkButton(self.custom_titlebar, text="X", width=30, command=self.on_close)
        self.minimize_btn = ctk.CTkButton(self.custom_titlebar, text="-", width=30, command=self.minimize_window)
        self.maximize_btn = ctk.CTkButton(self.custom_titlebar, text="□", width=30, command=self.maximize_window)
        self.close_btn.pack(side="right", padx=(0,5))
        self.maximize_btn.pack(side="right")
        self.minimize_btn.pack(side="right")

        self.custom_titlebar.bind("<B1-Motion>", self.move_window)
        self.custom_titlebar.bind("<Button-1>", self.click_window)
        self.offset_x = 0
        self.offset_y = 0

    def click_window(self, event):
        self.offset_x = event.x
        self.offset_y = event.y

    def move_window(self, event):
        x = self.window.winfo_pointerx() - self.offset_x
        y = self.window.winfo_pointery() - self.offset_y
        self.window.geometry(f"+{x}+{y}")

    def minimize_window(self):
        self.window.iconify()

    def maximize_window(self):
        if self.window.state() == "normal":
            self.window.state("zoomed")
        else:
            self.window.state("normal")

    # ----------------- 7ETW --------------------
    def save_execution(self, code):
        try:
            with open("executions.json", "r") as f:
                executions_history = json.load(f)
        except Exception:
            executions_history = []

        exec_number = len(executions_history) + 1
        exec_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        executions_history.append({"number": exec_number, "time": exec_time, "code": code})

        with open("executions.json", "w") as f:
            json.dump(executions_history, f, indent=4)

    def show_executions_history(self):
        try:
            with open("executions.json", "r") as f:
                executions_history = json.load(f)
        except Exception:
            executions_history = []

        history_window = ctk.CTkToplevel(self.window)
        history_window.title("7 Executions This Week (7ETW)")
        history_window.geometry("400x300")
        history_window.configure(fg_color=self.config["bg_color"])

        text_box = tk.Text(
            history_window,
            wrap="word",
            font=("JetBrains Mono", self.config["font_size"]),
            bg=self.config["bg_color"],
            fg=self.config["fg_color"],
            insertbackground=self.config["fg_color"],
            borderwidth=0,
            relief="flat",
            padx=10,
            pady=10
        )
        text_box.pack(expand=True, fill="both", padx=10, pady=10)
        text_box.configure(state="normal")
        text_box.insert("1.0", "=== 7 Executions This Week ===\n\n")
        for item in executions_history[-7:]:
            text_box.insert("end", f"Execution {item['number']}: {item['time']}\n")
        text_box.configure(state="disabled")
