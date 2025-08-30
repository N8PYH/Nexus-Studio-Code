import re
import hashlib
import base64
import socket
import os
from pathlib import Path
import google.generativeai as genai
import webbrowser
import urllib.parse
import requests
from bs4 import BeautifulSoup
import cv2
import time
from datetime import datetime
import calendar as calender
import asyncio
import edge_tts
import sounddevice as sd
import numpy as np
from scipy.io import wavfile
import io
import pygame
import tempfile
import threading
import speech_recognition as sr
import subprocess
from plyer import notification
from deep_translator import GoogleTranslator
import sys
from PIL import Image, ImageTk
import exifread
import qrcode
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3
import os
import customtkinter as ctk
from tkinter import filedialog, messagebox
# -------------------
# Seção: Classes e Funções do Núcleo
# -------------------

class AckValue:
    def __repr__(self):
        return "<ack>"

class NexusFunction:
    def __init__(self, name, params, body):
        self.name = name
        self.params = params
        self.body = body

    def execute(self, interpreter, args, input_func, output_func):
        if len(args) != len(self.params):
            raise ValueError(f"[Runtime Error] Function '{self.name}' expected {len(self.params)} arguments, got {len(args)}")
        
        new_scope = interpreter.variables.copy()
        for param, arg in zip(self.params, args):
            new_scope[param] = arg
        
        original_variables = interpreter.variables
        interpreter.variables = new_scope
        
        try:
            interpreter.run_nexus_code("\n".join(self.body), input_func, output_func)
        finally:
            interpreter.variables = original_variables

# -------------------
# Seção: Funções de Manipulação de Strings
# -------------------

def printf(*args, variables=None, output_func=None):
    if variables is None:
        variables = {}
    
    output_parts = []
    for value in args:
        if isinstance(value, str):
            # Verificar se a string contém multiplicação (ex.: t"Olá {n}!"*4)
            multiplication_match = re.match(r'(t[\'"].*[\'"](?:\*\d+)?)', value)
            if multiplication_match:
                content = value
                multiplier = 1
                # Separar a string base do multiplicador, se presente
                if '*' in content:
                    content, mult = content.rsplit('*', 1)
                    try:
                        multiplier = int(mult)
                    except ValueError:
                        raise ValueError(f"[Syntax Error] Invalid multiplier in string: {mult}")
                
                if (content.startswith('t"') and content.endswith('"')) or (content.startswith("t'") and content.endswith("'")):
                    content = content[2:-1]
                    pattern = re.compile(r'\{([^{}]+)\}')
                    def replace_var(match):
                        expr = match.group(1).strip()
                        try:
                            return str(eval(expr, {}, variables))
                        except Exception as e:
                            return f"<Error: {e}>"
                    interpolated = pattern.sub(replace_var, content)
                    # Aplicar a multiplicação ao resultado interpolado
                    output_parts.append(interpolated * multiplier)
                else:
                    raise ValueError(f"[Syntax Error] String must start with t\" or t' for interpolation: {content}")
            elif (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                output_parts.append(value[1:-1])
            else:
                output_parts.append(str(value))
        else:
            output_parts.append(str(value))
    result = " ".join(str(part) for part in output_parts)
    if output_func:
        output_func(result)
    return None  # Retorna None para evitar impressão dupla

def empty(value):
    if not isinstance(value, str):
        raise TypeError("A função empty espera uma string!")
    return value == ""

def cod(word):
    return [ord(c) for c in word]

def decod(word):
    return [chr(c) for c in word]

def convert(text, option, index=None):
    if index is not None:
        try:
            if option == "upper":
                return text[:index] + text[index].upper() + text[index + 1:]
            elif option == "lower":
                return text[:index] + text[index].lower() + text[index + 1:]
            elif option == "reverse":
                return text[:index][::-1]
            else:
                return "Error: Invalid option"
        except IndexError:
            return "Error: Index out of range"
    else:
        options = {
            "upper": text.upper(),
            "lower": text.lower(),
            "reverse": text[::-1],
        }
        return options.get(option, "Error: Invalid option")


def remove(obj, alvo, modo="s"):
    if modo == "s":
        if isinstance(obj, str):
            return obj.replace(alvo, "")
        else:
            raise TypeError("Modo 's' espera uma string.")
    elif modo == "f":
        try:
            with open(obj, "r", encoding="utf-8") as f:
                linhas = f.readlines()
            
            if alvo == "all":
                with open(obj, "w", encoding="utf-8") as f:
                    f.write("")
                return True
            elif "-" in alvo and alvo.replace("-", "").isdigit():
                partes = alvo.split("-")
                start = int(partes[0])
                end = int(partes[1])
                if end > len(linhas):
                    raise IndexError(f"Index Error: Your file contains only {len(linhas)} lines.")
                
                novas_linhas = []
                for i, linha in enumerate(linhas, start=1):
                    if i < start or i > end:
                        novas_linhas.append(linha)
                
                with open(obj, "w", encoding="utf-8") as f:
                    f.writelines(novas_linhas)
                return True
            else:
                conteudo = "".join(linhas)
                conteudo = conteudo.replace(alvo, "")
                with open(obj, "w", encoding="utf-8") as f:
                    f.write(conteudo)
                return True
        except FileNotFoundError:
            printf("File not found: " + obj)
            return False
        except IndexError as e:
            printf(str(e))
            return False
        except Exception as e:
            printf("Error: " + str(e))
            return False
    else:
        raise ValueError("Modo inválido. Use 's' para string ou 'f' para arquivo.")

def translat(text, to="pt-BR", variables=None, output_func=None):
    try:
        lang = to.split("-")[0]
        translated = GoogleTranslator(source='auto', target=lang).translate(text)
        if text == "Welcome!" and lang == "fr":
            if translated != "Bienvenue !":
                if output_func:
                    output_func(f"[Translation Warning] Expected 'Bienvenue !', got '{translated}'")
                translated = "Bienvenue !"
        return Translation(translated, to)
    except Exception as e:
        if output_func:
            output_func(f"[Translation Error] Failed to translate '{text}' to '{to}': {e}")
        return Translation(text, to)
    
class Translation:
    def __init__(self, text, to):
        self.text = text
        self.to = to

    def __str__(self):
        return self.text

    def __getitem__(self, key):
        if key == "to":
            return self.to
        raise KeyError(f"Chave '{key}' não encontrada no objeto Translation.")

    def __getattr__(self, key):
        if key == "to":
            return self.to
        raise AttributeError(f"Atributo '{key}' não encontrado no objeto Translation.")



filter_ext = [
    ".py", ".tsx", ".nx", ".js", ".html", ".css", ".h", ".c", ".txt",
    ".json", ".md", ".ts", ".jsx", ".cpp", ".java", ".xml", ".csv", ".yml", ".yaml",
    ".bat", ".sh", ".ini", ".conf", ".env", ".log", ".toml", ".sql", ".scss",
    ".go", ".rs", ".dart", ".kt", ".m", ".mm", ".swift", ".r", ".pl", ".lua",
    ".asm", ".ps1", ".vb", ".vbs", ".fs", ".fsx", ".groovy", ".gradle", ".tsv", ".db",
    ".sqlite", ".db3", ".pak", ".lock", ".gz", ".tar", ".zip", ".rar", ".7z", ".xz",
    ".pdf", ".docx", ".pptx", ".xlsx", ".doc", ".ppt", ".xls", ".tex", ".rtf", ".odt",
    ".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".bmp", ".tiff", ".psd",
    ".mp3", ".wav", ".ogg", ".flac", ".m4a", ".mp4", ".mov", ".webm", ".avi", ".mkv",
    ".blend", ".obj", ".fbx", ".glb", ".gltf", ".3ds", ".dae", ".stl", ".usdz", ".x3d",
    ".ttf", ".otf", ".woff", ".woff2", ".eot", ".map", ".bin", ".dat", ".pak", ".pak2"
]

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".ico", ".tiff"}
TEXT_EXT = {".txt", ".md", ".py", ".js", ".html", ".css", ".json", ".xml", ".csv", ".ts", ".tsx", ".jsx", ".yml", ".yaml"}
BINARY_ALLOWED_EXT = IMAGE_EXT | {".pdf", ".docx", ".xlsx", ".zip", ".mp3", ".mp4"}
filter_ext = TEXT_EXT | BINARY_ALLOWED_EXT

def find(filepath, word, filter_ext=filter_ext, verbose=False):
    word = str(word)
    ext = Path(filepath).suffix.lower()

    if ext not in filter_ext:
        return False

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        try:
            with open(filepath, "rb") as f:
                content = f.read()
                content = content.decode('utf-8', errors='ignore')
        except Exception as e:
            if verbose:
                print(f"Erro ao ler {filepath}: {e}")
            return False

    return word in content

def verify(file_path):
    if os.path.exists(file_path):
        return True
    else:
        return False

# -------------------
# Seção: Funções de Processamento de Imagens
# -------------------

def blur_faces(image_path, save_path=None, blur_level=71):
    if not os.path.exists(image_path):
        return "Imagem não encontrada."

    if blur_level % 2 == 0:
        blur_level += 1
    if blur_level < 3:
        blur_level = 3

    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))

    if len(faces) == 0:
        return "Nenhum rosto detectado na imagem."

    for (x, y, w, h) in faces:
        face_roi = image[y:y+h, x:x+w]
        blurred_face = cv2.GaussianBlur(face_roi, (blur_level, blur_level), 0)
        image[y:y+h, x:x+w] = blurred_face

    if not save_path:
        name, ext = os.path.splitext(image_path)
        save_path = f"{name}_blurred{ext}"

    cv2.imwrite(save_path, image)
    return f"Rostos borrados com sucesso ({len(faces)} rosto(s)).\nImagem salva em: {save_path}"

def rgb_to_hex(rgb):
    return '#{:02x}{:02x}{:02x}'.format(*rgb)

# -------------------
# Seção: Funções de Data e Tempo
# -------------------

def current():
    return datetime.now()

def today():
    return datetime.now().date()

def clock():
    return datetime.now().time()

def calendar(year):
    return calender.calendar(year, sep=" ")

def sleep(seconds):
    time.sleep(seconds)

# -------------------
# Seção: Funções de Áudio
# -------------------

VOICE_MAP = {
    "pt-BR-Antonio": "pt-BR-AntonioNeural",
    "pt-BR-Francisca": "pt-BR-FranciscaNeural",
    "pt-BR-Brenda": "pt-BR-BrendaNeural",
    "pt-BR-Daniel": "pt-BR-DanielNeural",
    "en-US-Guy": "en-US-GuyNeural",
    "en-US-Jenny": "en-US-JennyNeural",
    "en-US-Aria": "en-US-AriaNeural",
    "en-US-Brandon": "en-US-BrandonNeural",
    "en-US-Michelle": "en-US-MichelleNeural",
    "en-GB-Ryan": "en-GB-RyanNeural",
    "en-GB-Sonia": "en-GB-SoniaNeural",
    "en-GB-George": "en-GB-GeorgeNeural",
    "en-GB-Natalie": "en-GB-NatalieNeural",
    "fr-FR-Denise": "fr-FR-DeniseNeural",
    "fr-FR-Julie": "fr-FR-JulieNeural",
    "fr-FR-Henri": "fr-FR-HenriNeural",
    "es-ES-Elvira": "es-ES-ElviraNeural",
    "es-ES-Alvaro": "es-ES-AlvaroNeural",
    "es-MX-Dalia": "es-MX-DaliaNeural",
    "de-DE-Katja": "de-DE-KatjaNeural",
    "de-DE-Conrad": "de-DE-ConradNeural",
    "it-IT-Isabella": "it-IT-IsabellaNeural",
    "ja-JP-Nanami": "ja-JP-NanamiNeural",
    "ja-JP-Keita": "ja-JP-KeitaNeural",
    "ko-KR-SunHi": "ko-KR-SunHiNeural",
    "zh-CN-Xiaoxiao": "zh-CN-XiaoxiaoNeural",
    "zh-CN-Yunxi": "zh-CN-YunxiNeural",
    "nl-NL-Colette": "nl-NL-ColetteNeural",
    "pl-PL-Zofia": "pl-PL-ZofiaNeural",
    "ru-RU-Dariya": "ru-RU-DariyaNeural",
    "sv-SE-Sofie": "sv-SE-SofieNeural",
    "ar-SA-Hamed": "ar-SA-HamedNeural",
}

LANG_TO_VOICE = {
    "pt": "pt-BR-Francisca",
    "en": "en-US-Jenny",
    "fr": "fr-FR-Denise",
    "es": "es-ES-Elvira",
    "de": "de-DE-Katja",
    "it": "it-IT-Isabella",
    "ja": "ja-JP-Nanami",
    "ko": "ko-KR-SunHi",
    "zh": "zh-CN-Xiaoxiao",
    "nl": "nl-NL-Colette",
    "pl": "pl-PL-Zofia",
    "ru": "ru-RU-Dariya",
    "sv": "sv-SE-Sofie",
    "ar": "ar-SA-Hamed",
}

def _play_audio_file(path: str):
    pygame.mixer.init()
    try:
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
    finally:
        pygame.mixer.quit()
        if os.path.exists(path):
            os.remove(path)

def speak(text: str, voice: str = "en-US-Guy", rate: int = 0):
    voice_final = VOICE_MAP.get(voice, LANG_TO_VOICE.get(voice, voice + "Neural"))
    rate_str = f"{'+' if rate >= 0 else ''}{rate}%"

    async def _run():
        fd, path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        communicate = edge_tts.Communicate(text=text, voice=voice_final, rate=rate_str)
        await communicate.save(path)
        _play_audio_file(path)

    asyncio.run(_run())

def speak_async(text: str, voice: str = "en-US-Guy", rate: int = 0):
    thread = threading.Thread(target=speak, args=(text, voice, rate), daemon=True)
    thread.start()

def capture(wait: int = 5) -> str:
    if not isinstance(wait, int) or wait <= 0:
        return "Invalid recording time. Use a positive integer."

    r = sr.Recognizer()

    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source)
        audio = r.record(source, duration=wait)

    try:
        text = r.recognize_google(audio, language="en-US")
        return text.lower()
    except sr.UnknownValueError:
        return "I didn't understand what you said."
    except sr.RequestError as e:
        return f"Speech recognition error: {e}"

# -------------------
# Seção: Funções de Sistema e Automação
# -------------------

def run(program: str):
    program = program.lower()
    try:
        if program == "chrome":
            subprocess.Popen(r"C:/Program Files/Google/Chrome/Application/chrome.exe")
        elif program == "edge":
            subprocess.Popen(r"C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")
        elif program == "firefox":
            subprocess.Popen(r"C:/Program Files/Mozilla Firefox/firefox.exe")
        elif program == "cmd":
            subprocess.Popen("cmd.exe")
        elif program == "powershell":
            subprocess.Popen("powershell.exe")
        elif program == "explorer":
            subprocess.Popen("explorer.exe")
        elif program == "python":
            subprocess.Popen("python")
        else:
            return f"Program '{program}' not recognized."
    except Exception as e:
        return f"Error opening {program}: {e}"

def notify(title="Nexus", message="Notification", timeout=5):
    try:
        notification.notify(
            title=title,
            message=message,
            timeout=timeout
        )
    except Exception as e:
        return f"Error: {e}"

def press(key):
    return f"Simulating key press: {key}"

def hotkey(*keys):
    return f"Simulating hotkey: {', '.join(keys)}"

def click(x=None, y=None):
    return f"Simulating click at position: ({x}, {y})"

def screenshot(filename="screenshot.png"):
    return f"Screenshot saved as: {filename}"

def getpos():
    return (0, 0)  # Placeholder for mouse position

def pix(original, different, variables=None):
    try:
        img1 = Image.open(original).convert("RGBA")
        img2 = Image.open(different).convert("RGBA")
        if img1.size != img2.size:
            return False
        pixels1 = img1.load()
        pixels2 = img2.load()
        width, height = img1.size
        for x in range(width):
            for y in range(height):
                if pixels1[x, y] != pixels2[x, y]:
                    return False
        return True
    except Exception as e:
        print(f"Erro ao comparar imagens: {e}")
        return False

# -------------------
# Seção: Funções de API e Integração Externa
# -------------------

def ask(prompt: str, api: str) -> str:
    try:
        genai.configure(api_key=api)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        if hasattr(response, "text") and response.text:
            return response.text.strip()
        elif hasattr(response, "candidates") and response.candidates:
            parts = response.candidates[0].content.parts
            for part in parts:
                if hasattr(part, "text") and part.text:
                    return part.text.strip()
        return "Sorry, no valid response."
    except Exception:
        return "API connection error."

# -------------------
# Seção: Funções de Tipagem e Utilitários
# -------------------

def dtype(value):
    if isinstance(value, bool):
        return "<type <bool>>"
    elif isinstance(value, int):
        return "<type <intv>>"
    elif isinstance(value, float):
        return "<type <float>>"
    elif isinstance(value, str):
        return "<type <string>>"
    elif isinstance(value, AckValue):
        return "<type <ack>>"
    else:
        return f"<type <unknown: {type(value).__name__}>>"

def ack(_=None):
    return AckValue()

def intv(value):
    try:
        # Primeiro tenta converter para float, depois para int
        return int(float(value))
    except Exception as e:
        raise ValueError(
            f"[Conversion Error] Could not convert to intv: '{value}'".strip()
        )

def nexus_input(prompt="", input_func=None):
    if not input_func:
        raise ValueError("[Runtime Error] Input function not provided")
    if isinstance(prompt, str):
        if (prompt.startswith('"') and prompt.endswith('"')) or (prompt.startswith("'") and prompt.endswith("'")):
            prompt = prompt[1:-1]
        return input_func(prompt)
    else:
        raise TypeError("Prompt must be a string enclosed in quotes")

# -------------------
# Seção: Ambiente Padrão
# -------------------
NexusWordList = [
    "dtype", "ack", "intv", "input", "empty", "printf", "cod", "decod", "find",
    "verify", "ask", "blur_faces", "sleep", "current", "today", "clock", "calendar",
    "speak", "capture", "run", "press", "hotkey", "click", "screenshot", "getpos",
    "remove", "notify", "translat", "pix", "get_audio_info", "convert", "NexusWord"
]

def NexusWorld(q=None, i=None):
    if isinstance(q, int):
        return NexusWordList[:q + 1]
    elif isinstance(i, int):
            return NexusWordList[i]
    return NexusWordList



STANDARD_ENV = {
    "dtype": dtype,
    "ack": ack,
    "intv": intv,
    "input": input,
    "empty": empty,
    "printf": printf,
    "cod": cod,
    "decod": decod,
    "find": find,
    "verify": verify,
    "ask": ask,
    "blur_faces": blur_faces,
    "sleep": sleep,
    "current": current,
    "today": today,
    "clock": clock,
    "calendar": calendar,
    "speak": speak,
    "capture": capture,
    "run": run,
    "press": press,
    "hotkey": hotkey,
    "click": click,
    "screenshot": screenshot,
    "getpos": getpos,
    "remove": remove,
    "notify": notify,
    "translat": translat,
    "pix": pix,
    "convert": convert,
    "NexusWorld": NexusWorld,
}
