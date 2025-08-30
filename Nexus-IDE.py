import customtkinter as ctk
import tkinter as tk
from tkinter import Menu, filedialog, Listbox, simpledialog, ttk, messagebox
import os
import subprocess
import threading
import queue
import json
import sys
import re
from uuid import uuid4
from core_nexus.interpreter import NexusInterpreter
from ui.Result_Window import ResultWindow
import platform
import time
import random

# Variáveis globais
auto_run_enabled = False
input_queue = queue.Queue()
# Use the user's home directory dynamically
current_file = os.path.join(os.path.expanduser("~"), "Documents", "Nexus", "main.nx")
recent_files_menu = None
variables_panel = None
variables_visible = False
variable_order = []
status_bar = None
status_line_label = None
status_col_label = None
last_file_modified_time = 0
editor_frame = None
menu_bar = None
current_font = None
textbox = None
minimap = False
minimap_frame = False
result_window = None
themes_menu = None
font_menu = None
highlight_words = {
    "printf": "#c678dd", "if": "#e5c07b", "else": "#e5c07b", "elif": "#e5c07b",
    "True": "#c678dd", "False": "#c678dd", "dtype": "#56b6c2",
    "include": "#61afef", "input": "#c678dd", 
    "reg": "#e5c07b", "reap": "#c678dd", "try": "#e5c07b", "catch": "#e5c07b",
    "as": "#e5c07b", "cod": "#e5c07b", "decod": "#e5c07b", "join": "#e5c07b",
    "find": "#c678dd", "verify": "#c678dd", "sleep": "#c678dd", "speak": "#c678dd", "capture": "#c678dd",
    "press": "#c678dd", "click": "#c678dd", "hotkey": "#e5c07b", "screenshot": "#c678dd", "getpos": "#e5c07b",
    "remove": "#e5c07b", "notify": "#c678dd", "translat": "#c678dd", "pix": "#c678dd", "empty": "#c678dd",
    "convert": "#e5c07b", "NexusWorld": "#128539"
}

# Configuração padrão
config = {
    "bg_color": "#1a1a1a",
    "font_name": "JetBrains Mono",
    "font_size": 14,
    "fg_color": "#d4d4d4",
    "indent_chars": "    ",
    "theme": "dark",
    "autosave": True,
    "autosave_interval": 300000,
    "accent_color": "#2f80ed",
    "selection_color": "#3b5998",
    "toolbar_bg": "#2d2d2d",
    "toolbar_fg": "#ffffff",
    "menu_bg": "#262626",
    "menu_fg": "#d4d4d4",
    "status_bar_bg": "#2d2d2d",
    "status_bar_fg": "#d4d4d4",
    "panel_bg": "#262626",
    "panel_fg": "#d4d4d4",
    "active_line_bg": "#2a2a2a",
    "minimap_bg": "#2d2d2d",
    "minimap_font_size": 4
}

def load_config():
    global config, highlight_words
    config_path = os.path.join(os.path.expanduser("~"), "Documents", "Nexus", "system", "settings", "interface", "current_theme.json")
    highlight_path = os.path.join(os.path.expanduser("~"), "Documents", "Nexus", "system", "settings", "interface", "highlight_colors.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding='utf-8') as f:
                loaded_config = json.load(f)
                config.update(loaded_config.get("settings", {}))
                current_theme = loaded_config.get("current_theme", "dark")
        except json.JSONDecodeError:
            print("Error loading configuration. Using default settings.")
            current_theme = "dark"
    else:
        current_theme = "dark"
    
    if os.path.exists(highlight_path):
        try:
            with open(highlight_path, "r", encoding='utf-8') as f:
                highlight_words.update(json.load(f))
        except json.JSONDecodeError:
            print("Error loading highlight colors. Using default colors.")
    
    return current_theme

def save_config():
    config_path = os.path.join(os.path.expanduser("~"), "Documents", "Nexus", "system", "settings", "interface", "current_theme.json")
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    try:
        with open(config_path, "r", encoding='utf-8') as f:
            existing_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        existing_data = {"themes": {}}
    
    existing_data["current_theme"] = config["theme"]
    existing_data["settings"] = config
    
    try:
        with open(config_path, "w", encoding='utf-8') as f:
            json.dump(existing_data, f, indent=4)
    except Exception as e:
        print(f"Error saving configuration: {e}")

def reload_window():
    global highlight_words
    if textbox.edit_modified():
        response = messagebox.askyesno("Save Changes", "Do you want to save changes before reloading?")
        if response:
            save_file()
    
    current_theme = load_config()
    
    # Reconfigurar menus
    menu_bar.delete(0, "end")
    menu_bar.add_cascade(label="File", menu=file_menu)
    menu_bar.add_cascade(label="Run", menu=run_menu)
    menu_bar.add_cascade(label="Style", menu=style_menu)
    menu_bar.add_cascade(label="Apps", menu=apps_menu)
    
    update_recent_files_menu()
    update_themes_menu()
    
    # Reaplicar tema atual
    apply_theme(current_theme, force_apply=True)
    
    # Reconfigurar textbox
    textbox.config(
        bg=config["bg_color"],
        fg=config["fg_color"],
        selectbackground=config["selection_color"],
        font=(config["font_name"], config["font_size"])
    )
    editor_frame.configure(fg_color=config["bg_color"])
    status_bar.configure(bg=config["status_bar_bg"])
    status_line_label.configure(bg=config["status_bar_bg"], fg=config["status_bar_fg"])
    status_col_label.configure(bg=config["status_bar_bg"], fg=config["status_bar_fg"])
    
    # Reconfigurar highlight_words
    for word, color in highlight_words.items():
        textbox.tag_config(word, foreground=color)
    
    textbox.tag_config("double_string", foreground="#98c379")
    textbox.tag_config("single_string", foreground="#98c379")
    textbox.tag_config("comment", foreground="#e06c75")
    textbox.tag_config("super_comment", foreground="#e06c75")
    textbox.tag_config("active_line", background=config["active_line_bg"])
    
    highlight_text()
    update_ui_state()

def uninstall_theme(theme_name):
    if theme_name in ["dark", "light"]:
        messagebox.showwarning("Warning", "Cannot uninstall default themes (Dark or Light).")
        return
    
    config_path = os.path.join(os.path.expanduser("~"), "Documents", "Nexus", "system", "settings", "interface", "current_theme.json")
    try:
        with open(config_path, "r", encoding='utf-8') as f:
            data = json.load(f)
        themes = data.get("themes", {})
        if theme_name in themes:
            del themes[theme_name]
            data["themes"] = themes
            if data.get("current_theme") == theme_name:
                data["current_theme"] = "dark"
                apply_theme("dark", force_apply=True)
            with open(config_path, "w", encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            messagebox.showinfo("Success", f"Theme '{theme_name}' uninstalled successfully.")
            update_themes_menu()
        else:
            messagebox.showerror("Error", f"Theme '{theme_name}' not found.")
    except Exception as e:
        messagebox.showerror("Error", f"Error uninstalling theme: {e}")

def resolve_theme_issues(theme_name):
    config_path = os.path.join(os.path.expanduser("~"), "Documents", "Nexus", "system", "settings", "interface", "current_theme.json")
    try:
        with open(config_path, "r", encoding='utf-8') as f:
            data = json.load(f)
        themes = data.get("themes", {})
        if theme_name not in themes and theme_name not in ["dark", "light"]:
            messagebox.showerror("Error", f"Theme '{theme_name}' not found.")
            return
        
        apply_theme(theme_name, force_apply=True)
        messagebox.showinfo("Success", f"Theme '{theme_name}' reapplied successfully.")
    except json.JSONDecodeError:
        messagebox.showerror("Error", "Invalid theme configuration file. Resetting to default.")
        apply_theme("dark", force_apply=True)
        save_config()
    except Exception as e:
        messagebox.showerror("Error", f"Error resolving theme issues: {e}")

def update_themes_menu():
    global themes_menu
    themes_menu.delete(0, "end")
    config_path = os.path.join(os.path.expanduser("~"), "Documents", "Nexus", "system", "settings", "interface", "current_theme.json")
    theme_names = ["dark", "light"]
    
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding='utf-8') as f:
                loaded_config = json.load(f)
                themes = loaded_config.get("themes", {})
                theme_names.extend([name for name in themes.keys() if name not in ["dark", "light"]])
        except json.JSONDecodeError:
            print("Error loading themes. Using default themes.")
    
    if len(theme_names) > 80:
        theme_names = theme_names[:80]
    
    def create_context_menu(theme_name):
        context_menu = Menu(themes_menu, tearoff=0, bg=config["menu_bg"], fg=config["menu_fg"])
        context_menu.add_command(label="Uninstall", command=lambda: [uninstall_theme(theme_name), reload_window()])
        context_menu.add_command(label="Resolve Problems", command=lambda: [resolve_theme_issues(theme_name), reload_window()])
        return context_menu
    
    for theme_name in theme_names:
        themes_menu.add_command(
            label=theme_name.capitalize(),
            command=lambda t=theme_name: apply_theme(t, force_apply=True)
        )
        def show_context_menu(event, t=theme_name):
            if t not in ["dark", "light"]:  # Impede que temas padrão sejam desinstalados
                context_menu = create_context_menu(t)
                context_menu.post(event.x_root, event.y_root)
        themes_menu.entryconfig(theme_name.capitalize(), command=lambda t=theme_name: apply_theme(t, force_apply=True))
        themes_menu.bind("<Button-3>", lambda event, t=theme_name: show_context_menu(event, t))

def apply_theme(theme_name, force_apply=False):
    global config
    if not force_apply and config.get("theme") == theme_name:
        return
    
    theme = {
        "dark": {
            "bg": "#1a1a1a", "fg": "#d4d4d4",
            "accent": "#2f80ed", "selection": "#3b5998", "toolbar": "#2d2d2d", "menu": "#262626",
            "status_bar": "#2d2d2d", "panel": "#262626", "active_line_bg": "#2a2a2a"
        },
        "light": {
            "bg": "#ffffff", "fg": "#333333",
            "accent": "#007acc", "selection": "#add6ff", "toolbar": "#e0e0e0", "menu": "#f5f5f5",
            "status_bar": "#e0e0e0", "panel": "#f5f5f5", "active_line_bg": "#f0f0f0"
        }
    }.get(theme_name)

    if not theme:
        config_path = os.path.join(os.path.expanduser("~"), "Documents", "Nexus", "system", "settings", "interface", "current_theme.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    settings = loaded_config.get("settings", {})
                    theme = {
                        "bg": settings.get("bg_color", "#1a1a1a"),
                        "fg": settings.get("fg_color", "#d4d4d4"),
                        "accent": settings.get("accent_color", "#2f80ed"),
                        "selection": settings.get("selection_color", "#3b5998"),
                        "toolbar": settings.get("toolbar_bg", "#2d2d2d"),
                        "menu": settings.get("menu_bg", "#262626"),
                        "status_bar": settings.get("status_bar_bg", "#2d2d2d"),
                        "panel": settings.get("panel_bg", "#262626"),
                        "active_line_bg": settings.get("active_line_bg", "#2a2a2a")
                    }
            except json.JSONDecodeError:
                print("Error loading custom theme. Falling back to dark theme.")
                theme = {
                    "bg": "#1a1a1a", "fg": "#d4d4d4",
                    "accent": "#2f80ed", "selection": "#3b5998", "toolbar": "#2d2d2d", "menu": "#262626",
                    "status_bar": "#2d2d2d", "panel": "#262626", "active_line_bg": "#2a2a2a"
                }
        else:
            theme = {
                "bg": "#1a1a1a", "fg": "#d4d4d4",
                "accent": "#2f80ed", "selection": "#3b5998", "toolbar": "#2d2d2d", "menu": "#262626",
                "status_bar": "#2d2d2d", "panel": "#262626", "active_line_bg": "#2a2a2a"
            }

    config["theme"] = theme_name
    config["bg_color"] = theme["bg"]
    config["fg_color"] = theme["fg"]
    config["accent_color"] = theme["accent"]
    config["selection_color"] = theme["selection"]
    config["toolbar_bg"] = theme["toolbar"]
    config["menu_bg"] = theme["menu"]
    config["status_bar_bg"] = theme["status_bar"]
    config["panel_bg"] = theme["panel"]
    config["active_line_bg"] = theme["active_line_bg"]

    root.configure(fg_color=theme["bg"])
    if editor_frame:
        editor_frame.configure(fg_color=theme["bg"])
    if textbox:
        textbox.config(bg=theme["bg"], fg=theme["fg"], selectbackground=theme["selection"])
        textbox.tag_configure("active_line", background=config["active_line_bg"])
    if status_bar:
        status_bar.configure(bg=theme["status_bar"])
        status_line_label.configure(bg=theme["status_bar"], fg=theme["fg"])
        status_col_label.configure(bg=theme["status_bar"], fg=theme["fg"])
    if variables_panel and variables_visible:
        variables_panel.configure(fg_color=theme["panel"])
        variables_panel.listbox.configure(bg=theme["panel"], fg=theme["fg"], 
                                        selectbackground=theme["accent"])
    if menu_bar:
        menu_bar.configure(bg=theme["menu"], fg=theme["fg"])
        for menu in (file_menu, run_menu, style_menu, apps_menu, recent_files_menu, themes_menu, font_menu):
            menu.configure(bg=theme["menu"], fg=theme["fg"])
    if result_window:
        result_window.apply_theme(config)
    
    save_config()
    update_ui_state()
    update_themes_menu()

def update_current_file_json():
    cursor_pos = textbox.index("insert")
    cursor_line = int(cursor_pos.split(".")[0])
    current_file_path = os.path.join(os.path.expanduser("~"), "Documents", "Nexus", "system", "settings", "files", "current_file.json")
    os.makedirs(os.path.dirname(current_file_path), exist_ok=True)
    try:
        with open(current_file_path, "w", encoding='utf-8') as f:
            json.dump({"current_file": current_file, "cursor_line": cursor_line}, f, indent=4)
    except Exception as e:
        print(f"Error updating current_file.json: {e}")

def update_ui_state(title=None):
    update_status_bar()
    update_variables_list()
    if title:
        root.title(title)
    textbox.edit_modified(False)
    update_current_file_json()

def setup_status_bar():
    global status_bar, status_line_label, status_col_label
    status_bar = tk.Frame(root, bg=config["status_bar_bg"])
    status_bar.pack(side="bottom", fill="x")
    status_line_label = tk.Label(status_bar, text="Linha: 1", bg=config["status_bar_bg"], fg=config["status_bar_fg"])
    status_line_label.pack(side="left", padx=5)
    status_col_label = tk.Label(status_bar, text="Coluna: 1", bg=config["status_bar_bg"], fg=config["status_bar_fg"])
    status_col_label.pack(side="left", padx=5)

def update_status_bar(event=None):
    if status_bar:
        cursor_pos = textbox.index("insert")
        line, col = cursor_pos.split(".")
        status_line_label.config(text=f"Linha: {line}")
        status_col_label.config(text=f"Coluna: {int(col) + 1}")
        textbox.edit_modified(False)

def check_file_modification():
    global last_file_modified_time
    if current_file and os.path.exists(current_file):
        try:
            current_mtime = os.path.getmtime(current_file)
            if current_mtime > last_file_modified_time:
                with open(current_file, "r", encoding='utf-8') as f:
                    content = f.read()
                textbox.delete("1.0", "end")
                textbox.insert("1.0", content)
                last_file_modified_time = current_mtime
                update_ui_state(f"Nexus Studio - {current_file}")
        except Exception as e:
            print(f"Error checking file modification: {e}")
    root.after(1000, check_file_modification)

def load_file_from_arg(file_path):
    global current_file, last_file_modified_time
    if file_path and os.path.exists(file_path) and file_path.endswith('.nx'):
        try:
            with open(file_path, "r", encoding='utf-8') as file:
                content = file.read()
                textbox.delete("1.0", "end")
                textbox.insert("1.0", content)
                current_file = file_path
                last_file_modified_time = os.path.getmtime(file_path)
                update_recent_files(file_path)
                update_ui_state(f"Nexus Studio - {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not open the file: {e}")
    else:
        messagebox.showerror("Error", f"File {file_path} not found or is not an .nx file")

def open_file():
    global current_file, last_file_modified_time
    file_path = filedialog.askopenfilename(defaultextension=".nx", 
                                          filetypes=[("Nexus Files", "*.nx")])
    if file_path:
        try:
            with open(file_path, "r", encoding='utf-8') as file:
                content = file.read()
                textbox.delete("1.0", "end")
                textbox.insert("1.0", content)
                current_file = file_path
                last_file_modified_time = os.path.getmtime(file_path)
                update_recent_files(file_path)
                update_ui_state(f"Nexus Studio - {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not open the file: {e}")

def save_file():
    global current_file
    if current_file and os.path.exists(current_file):
        try:
            with open(current_file, "w", encoding='utf-8') as file:
                content = textbox.get("1.0", "end-1c")
                file.write(content)
            update_ui_state()
            global last_file_modified_time
            last_file_modified_time = os.path.getmtime(current_file)
            update_current_file_json()
        except Exception as e:
            messagebox.showerror("Error", f"Could not save the file: {e}")
    else:
        save_file_as()

def save_file_as():
    global current_file, last_file_modified_time
    file_path = filedialog.asksaveasfilename(defaultextension=".nx", 
                                            filetypes=[("Nexus Files", "*.nx")])
    if file_path:
        if not file_path.endswith('.nx'):
            file_path += '.nx'
        try:
            with open(file_path, "w", encoding='utf-8') as file:
                content = textbox.get("1.0", "end-1c")
                file.write(content)
            current_file = file_path
            last_file_modified_time = os.path.getmtime(file_path)
            update_recent_files(file_path)
            update_ui_state(f"Nexus Studio - {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save the file: {e}")

def update_recent_files(file_path):
    recent_files = []
    recent_files_path = os.path.join(os.path.expanduser("~"), "Documents", "Nexus", "system", "settings", "files", "recent_files.json")
    os.makedirs(os.path.dirname(recent_files_path), exist_ok=True)
    if os.path.exists(recent_files_path):
        try:
            with open(recent_files_path, "r", encoding='utf-8') as f:
                recent_files = json.load(f)
                if not isinstance(recent_files, list):
                    recent_files = []
        except json.JSONDecodeError:
            recent_files = []
    if file_path and os.path.exists(file_path):
        if file_path in recent_files:
            recent_files.remove(file_path)
        recent_files.insert(0, file_path)
        recent_files = recent_files[:10]
    try:
        with open(recent_files_path, "w", encoding='utf-8') as f:
            json.dump(recent_files, f, indent=4)
    except Exception as e:
        print(f"Error saving recent files: {e}")
    update_recent_files_menu()

def update_recent_files_menu():
    global recent_files_menu
    recent_files_path = os.path.join(os.path.expanduser("~"), "Documents", "Nexus", "system", "settings", "files", "recent_files.json")
    recent_files = []
    if os.path.exists(recent_files_path):
        try:
            with open(recent_files_path, "r", encoding='utf-8') as f:
                recent_files = json.load(f)
                if not isinstance(recent_files, list):
                    recent_files = []
        except json.JSONDecodeError:
            recent_files = []
    recent_files_menu.delete(0, "end")
    if not recent_files:
        recent_files_menu.add_command(label="No recent files", state="disabled")
    else:
        for i, file_path in enumerate(recent_files):
            if os.path.exists(file_path):
                def make_command(path=file_path):
                    return lambda: open_recent_file(path)
                recent_files_menu.add_command(
                    label=os.path.basename(file_path),
                    command=make_command()
                )
            else:
                recent_files.remove(file_path)
                try:
                    with open(recent_files_path, "w", encoding='utf-8') as f:
                        json.dump(recent_files, f, indent=4)
                except Exception as e:
                    print(f"Error updating recent files: {e}")

def open_recent_file(file_path):
    global current_file, last_file_modified_time
    if not os.path.exists(file_path):
        messagebox.showerror("Error", f"File {file_path} not found")
        update_recent_files("")
        return
    try:
        with open(file_path, "r", encoding='utf-8') as file:
            content = file.read()
            textbox.delete("1.0", "end")
            textbox.insert("1.0", content)
            current_file = file_path
            last_file_modified_time = os.path.getmtime(file_path)
            update_recent_files(file_path)
            update_ui_state(f"Nexus Studio - {file_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Could not open the file: {e}")
        update_recent_files("")

def new_file():
    global current_file, last_file_modified_time
    if textbox.edit_modified():
        response = messagebox.askyesnocancel("Save Changes", "Do you want to save changes before creating a new file?")
        if response is True:
            save_file()
        elif response is False:
            pass
        else:
            return
    textbox.delete("1.0", "end")
    current_file = None
    last_file_modified_time = 0
    update_ui_state("Nexus Studio - New File")
    update_recent_files("")
    textbox.edit_modified(False)

def save_changes_dialog():
    if textbox.edit_modified():
        response = messagebox.askyesnocancel("Save Changes", "Do you want to save changes before continuing?")
        if response is True:
            save_file()
            return True
        elif response is False:
            return True
        else:
            return False
    return True

def autosave():
    if config["autosave"] and current_file:
        save_file()
    root.after(config["autosave_interval"], autosave)

def open_terminal():
    try:
        subprocess.Popen(["python", os.path.join(os.path.expanduser("~"), "Documents", "Nexus", "system", "settings", "apps", "terminal.py")], shell=False)
    except Exception as e:
        messagebox.showerror("Error", f"Could not open the terminal: {e}")

def open_pixpaint():
    try:
        subprocess.Popen(["python", os.path.join(os.path.expanduser("~"), "Documents", "Nexus", "assets", "apps", "PixPaint", "pixpaint.py")], shell=False)
    except Exception as e:
        messagebox.showerror("Error", f"Could not open the PixPaint: {e}")

def run_code():
    global result_window
    if not current_file:
        messagebox.showerror("Error", "Please save the file with .nx extension before running.")
        return
    if not current_file.endswith('.nx'):
        messagebox.showerror("Error", "Only .nx files can be executed.")
        return
    if textbox.edit_modified():
        if messagebox.askyesno("Unsaved Changes", "There are unsaved changes. Do you want to save before running?"):
            save_file()
        else:
            return

    code = textbox.get("1.0", "end-1c")
    result_window.execute_code(code)

def clear_console():
    if result_window:
        result_window.clear_console()

def change_font(font_name):
    global current_font
    current_font = (font_name, config["font_size"])
    textbox.config(font=current_font)
    config["font_name"] = font_name
    save_config()
    if result_window:
        result_window.apply_theme(config)

def adjust_font_size(size):
    global current_font
    config["font_size"] = int(size)
    current_font = (config["font_name"], config["font_size"])
    textbox.config(font=current_font)
    save_config()
    if result_window:
        result_window.apply_theme(config)

def open_font_size_slider():
    font_window = ctk.CTkToplevel(root)
    font_window.title("Font Size")
    font_window.geometry("300x100")
    font_window.resizable(False, False)
    font_window.configure(fg_color=config["bg_color"])
    
    ctk.CTkLabel(font_window, text="Select font size:", text_color=config["fg_color"]).pack(pady=10)
    
    button_frame = ctk.CTkFrame(font_window, fg_color=config["bg_color"])
    button_frame.pack(pady=5)
    
    font_sizes = [15, 20, 25, 30, 35, 40]
    for size in font_sizes:
        ctk.CTkButton(
            button_frame,
            text=str(size),
            width=50,
            command=lambda s=size: [adjust_font_size(s), font_window.destroy()],
            fg_color=config["accent_color"],
            hover_color="#1f5bb2"
        ).pack(side="left", padx=5)

def load_nxapps():
    nxapps_path = os.path.join(os.path.expanduser("~"), "Documents", "Nexus", "assets", "apps")
    apps = []
    if os.path.exists(nxapps_path):
        for item in os.listdir(nxapps_path):
            item_path = os.path.join(nxapps_path, item)
            if os.path.isfile(item_path) and item.endswith('.py'):
                apps.append(item)
            elif os.path.isdir(item_path):
                main_file = os.path.join(item_path, "main.py")
                if os.path.exists(main_file):
                    apps.append(item)
    return apps

def run_nxapp(app_name):
    nxapps_path = os.path.join(os.path.expanduser("~"), "Documents", "Nexus", "assets", "apps")
    app_path = os.path.join(nxapps_path, app_name)
    try:
        if os.path.isfile(app_path) and app_name.endswith(".py"):
            subprocess.Popen(["python", app_path], shell=False)
        elif os.path.isdir(app_path):
            main_file = os.path.join(app_path, "main.py")
            if os.path.exists(main_file):
                subprocess.Popen(["python", main_file], shell=False)
            else:
                messagebox.showerror("Error", f"main.py file not found in {app_name}")
    except Exception as e:
        messagebox.showerror("Error", f"Error running {app_name}: {e}")

autocomplete_pairs = {"(": ")", "[": "]", "{": "}", '"': '"', "'": "'"}

def autocomplete(event):
    char = event.char
    if char in autocomplete_pairs:
        cursor_pos = textbox.index("insert")
        textbox.insert(cursor_pos, autocomplete_pairs[char])
        textbox.mark_set("insert", cursor_pos)

def auto_indent(event):
    cursor_pos = textbox.index("insert")
    line_number = cursor_pos.split(".")[0]
    current_line = textbox.get(f"{line_number}.0", f"{line_number}.end").strip()
    if current_line.endswith(":"):
        textbox.insert("insert", "\n" + config["indent_chars"])
        return "break"
    else:
        prev_line = textbox.get(f"{int(line_number)-1}.0", f"{int(line_number)-1}.end")
        indent_match = re.match(r"^(\s+)", prev_line)
        if indent_match:
            indent = indent_match.group(1)
            textbox.insert("insert", "\n" + indent)
            return "break"
    return None

def insert_simple_code(event):
    cursor_pos = textbox.index("insert")
    simple_code = 'name = "John"\nprintf(name * 3)'
    textbox.insert(cursor_pos, simple_code)
    update_ui_state()
    return "break"

def insert_input_code(event):
    cursor_pos = textbox.index("insert")
    input_code = 'name = input("Enter your name: ")\nprintf(name)'
    textbox.insert(cursor_pos, input_code)
    update_ui_state()
    return "break"

def create_variables_panel():
    global variables_panel
    variables_panel = ctk.CTkFrame(root, fg_color=config["panel_bg"], corner_radius=8, height=150)
    variables_panel.pack_propagate(False)
    listbox = tk.Listbox(variables_panel, font=("JetBrains Mono", 12), bg=config["panel_bg"], 
                         fg=config["panel_fg"], selectbackground=config["accent_color"], 
                         borderwidth=0, height=8)
    listbox.pack(fill="both", expand=True, padx=5, pady=5)
    variables_panel.listbox = listbox
    
    def on_variable_select(event):
        selection = listbox.curselection()
        if selection:
            var_name = listbox.get(selection[0])
            messagebox.showinfo("Variable Info", f"Selected variable: {var_name}")
    
    listbox.bind("<<ListboxSelect>>", on_variable_select)
    update_variables_list()

def update_variables_list():
    global variable_order
    if not variables_panel or not hasattr(variables_panel, 'listbox'):
        return
    
    variables_panel.listbox.delete(0, "end")
    
    if hasattr(interpreter, 'variables'):
        for var_name, var_value in interpreter.variables.items():
            variables_panel.listbox.insert("end", f"{var_name} = {var_value}")

def setup_undo_redo():
    textbox.config(undo=True)
    textbox.edit_reset()

def highlight_text(event=None):
    for tag in highlight_words:
        textbox.tag_remove(tag, "1.0", "end")
    textbox.tag_remove("double_string", "1.0", "end")
    textbox.tag_remove("single_string", "1.0", "end")
    textbox.tag_remove("comment", "1.0", "end")
    textbox.tag_remove("super_comment", "1.0", "end")

    pos = "1.0"
    while True:
        comment_start = textbox.search('//', pos, stopindex="end")
        if not comment_start:
            break
        line_end = f"{comment_start.split('.')[0]}.end"
        line_content = textbox.get(comment_start, line_end)
        
        if line_content.startswith('// *') and line_content.endswith('*'):
            textbox.tag_add("super_comment", comment_start, line_end)
        else:
            textbox.tag_add("comment", comment_start, line_end)
        
        pos = f"{line_end}+1c"

    content = textbox.get("1.0", "end")
    for word, color in highlight_words.items():
        if word == "in":
            pattern = r'\bin\b'
        else:
            pattern = r'\b' + word + r'\b'
        for match in re.finditer(pattern, content):
            match_start = f"1.0 + {match.start()} chars"
            match_end = f"1.0 + {match.end()} chars"
            if not any(textbox.compare(match_start, ">=", s) and textbox.compare(match_end, "<=", e)
                       for s, e in zip(
                           (textbox.tag_ranges("double_string") + textbox.tag_ranges("single_string") +
                            textbox.tag_ranges("comment") + textbox.tag_ranges("super_comment"))[::2],
                           (textbox.tag_ranges("double_string") + textbox.tag_ranges("single_string") +
                            textbox.tag_ranges("comment") + textbox.tag_ranges("super_comment"))[1::2])):
                textbox.tag_add(word, match_start, match_end)

    pos = "1.0"
    while True:
        quote_start = textbox.search('"', pos, stopindex="end")
        if not quote_start:
            break
        quote_end = quote_start
        while True:
            next_quote = textbox.search('"', f"{quote_end}+1c", stopindex="end")
            if not next_quote:
                break
            prev_char = textbox.get(f"{next_quote}-1c")
            if prev_char != "\\" or textbox.get(f"{next_quote}-2c") == "\\":
                quote_end = next_quote
                break
            quote_end = next_quote
        if quote_end != quote_start:
            textbox.tag_add("double_string", quote_start, f"{quote_end}+1c")
        pos = f"{quote_end}+1c" if quote_end != quote_start else f"{quote_start}+1c"

    pos = "1.0"
    while True:
        quote_start = textbox.search("'", pos, stopindex="end")
        if not quote_start:
            break
        quote_end = quote_start
        while True:
            next_quote = textbox.search("'", f"{quote_end}+1c", stopindex="end")
            if not next_quote:
                break
            prev_char = textbox.get(f"{next_quote}-1c")
            if prev_char != "\\" or textbox.get(f"{next_quote}-2c") == "\\":
                quote_end = next_quote
                break
            quote_end = next_quote
        if quote_end != quote_start:
            textbox.tag_add("single_string", quote_start, f"{quote_end}+1c")
        pos = f"{quote_end}+1c" if quote_end != quote_start else f"{quote_start}+1c"

# Configuração inicial
root = ctk.CTk()
root.geometry("900x650")
root.title("Nexus IDE")

# Inicializa o interpretador e a janela de resultados
interpreter = NexusInterpreter()
result_window = ResultWindow(root, config, interpreter)

load_config()
current_font = (config["font_name"], config["font_size"])

editor_frame = ctk.CTkFrame(root, fg_color=config["bg_color"], corner_radius=8)
editor_frame.pack(expand=True, fill="both", padx=10, pady=10)

textbox = tk.Text(editor_frame, wrap="word", font=current_font, bg=config["bg_color"], fg=config["fg_color"],
                  selectbackground=config["selection_color"], borderwidth=0, padx=10, pady=10)
textbox.pack(expand=True, fill="both")

for word, color in highlight_words.items():
    textbox.tag_config(word, foreground=color)

textbox.tag_config("double_string", foreground="#98c379")
textbox.tag_config("single_string", foreground="#98c379")
textbox.tag_config("comment", foreground="#e06c75")
textbox.tag_config("super_comment", foreground="#e06c75")
textbox.tag_config("active_line", background=config["active_line_bg"])

# Bindings
textbox.bind("<KeyRelease>", lambda e: [highlight_text(e), update_status_bar(e), update_variables_list(), save_file()])
textbox.bind("<Return>", auto_indent)
for opening in autocomplete_pairs:
    textbox.bind(opening, autocomplete)
textbox.bind("<Button-1>", lambda e: [update_status_bar(e)])
textbox.bind("<Control-space>", insert_simple_code)
textbox.bind("<Control-y>", lambda e: [insert_input_code(e), "break"])
textbox.bind("<Control-s>", lambda e: [save_file(), "break"])
textbox.bind("<Control-o>", lambda e: [open_file(), "break"])
textbox.bind("<Control-n>", lambda e: [new_file(), "break"])
textbox.bind("<Control-r>", lambda e: [run_code(), "break"])
textbox.bind("<Control-z>", lambda e: [textbox.edit_undo(), "break"])
textbox.bind("<Control-y>", lambda e: [textbox.edit_redo(), "break"])

menu_bar = Menu(root, bg=config["menu_bg"], fg=config["menu_fg"])
file_menu = Menu(menu_bar, tearoff=0, bg=config["menu_bg"], fg=config["menu_fg"])
file_menu.add_command(label="New File", command=new_file, accelerator="Ctrl+N")
file_menu.add_command(label="Open File", command=open_file, accelerator="Ctrl+O")
file_menu.add_command(label="Save File", command=save_file, accelerator="Ctrl+S")
file_menu.add_command(label="Save As", command=save_file_as)
file_menu.add_command(label="Reload Window", command=reload_window)
recent_files_menu = Menu(file_menu, tearoff=0, bg=config["menu_bg"], fg=config["menu_fg"])
file_menu.add_cascade(label="Recent Files", menu=recent_files_menu)
file_menu.add_separator()
file_menu.add_command(label="Undo", command=textbox.edit_undo, accelerator="Ctrl+Z")
file_menu.add_command(label="Redo", command=textbox.edit_redo, accelerator="Ctrl+Shift+Z")

run_menu = Menu(menu_bar, tearoff=0, bg=config["menu_bg"], fg=config["menu_fg"])
run_menu.add_command(label="Run Code", command=run_code, accelerator="Ctrl+R")
run_menu.add_command(label="Clear Console", command=clear_console)

style_menu = Menu(menu_bar, tearoff=0, bg=config["menu_bg"], fg=config["menu_fg"])
themes_menu = Menu(style_menu, tearoff=0, bg=config["menu_bg"], fg=config["menu_fg"])
style_menu.add_cascade(label="Themes", menu=themes_menu)
style_menu.add_command(label="Adjust Font Size", command=open_font_size_slider)
font_menu = Menu(style_menu, tearoff=0, bg=config["menu_bg"], fg=config["menu_fg"])
font_menu.add_command(label="JetBrains Mono", command=lambda: change_font("JetBrains Mono"))
font_menu.add_command(label="Fira Code", command=lambda: change_font("Fira Code"))
font_menu.add_command(label="Source Code Pro", command=lambda: change_font("Source Code Pro"))
font_menu.add_command(label="Consolas", command=lambda: change_font("Consolas"))
font_menu.add_command(label="Courier New", command=lambda: change_font("Courier New"))
style_menu.add_cascade(label="Font", menu=font_menu)

apps_menu = Menu(menu_bar, tearoff=0, bg=config["menu_bg"], fg=config["menu_fg"])
apps_menu.add_command(label="Terminal", command=open_terminal)
apps_menu.add_command(label="PixPaint", command=open_pixpaint)
apps_menu.add_command(label="iTheme", command=lambda: run_nxapp("iTheme/itheme.py"))
nxapps = load_nxapps()
for app in nxapps:
    if app != "iTheme/itheme.py":
        apps_menu.add_command(label=app, command=lambda app=app: run_nxapp(app))

menu_bar.add_cascade(label="File", menu=file_menu)
menu_bar.add_cascade(label="Run", menu=run_menu)
menu_bar.add_cascade(label="Style", menu=style_menu)
menu_bar.add_cascade(label="Apps", menu=apps_menu)

# Finalização
root.config(menu=menu_bar)
setup_undo_redo()
setup_status_bar()
root.after(config["autosave_interval"], autosave)
root.after(1000, check_file_modification)
update_recent_files_menu()

theme_path = os.path.join(os.path.expanduser("~"), "Documents", "Nexus", "system", "settings", "interface", "current_theme.json")
if os.path.exists(theme_path):
    try:
        with open(theme_path, "r", encoding='utf-8') as f:
            saved_theme = json.load(f)
            apply_theme(saved_theme.get("current_theme", "dark"), force_apply=True)
    except json.JSONDecodeError:
        apply_theme("dark", force_apply=True)
else:
    apply_theme("dark", force_apply=True)

if len(sys.argv) > 1:
    load_file_from_arg(sys.argv[1])
    run_code()

root.mainloop()