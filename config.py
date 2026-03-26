import json
import os
import sys

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- Configuration & Paths ---
# Diese Dateien werden später IN die .exe gepackt:
LOCALES_DIR = resource_path("locales")
FLAGS_FILE = resource_path("audio_flags.json")

# Diese Dateien bleiben LOKAL neben der .exe:
CONFIG_FILE = "config.json" 
BIN_DIR = "bin"

# --- Media Constants ---
CODEC_OPTIONS = ["Copy", "AC3", "AAC", "MP3"]
FILTER_CODEC_OPTIONS = [c for c in CODEC_OPTIONS if c != "Copy"]
BITRATE_OPTIONS = ["Original", "128k", "192k", "256k", "320k", "640k"]
CHANNEL_OPTIONS = ["Original", "Stereo Downmix"]

# --- Global State ---
languages = {}
available_languages = []
audio_flags = {}
available_flags = []
current_config = {}
texts = {}

def init_config():
    global languages, available_languages, audio_flags, available_flags, current_config, texts
    
    if os.path.exists(LOCALES_DIR):
        for filename in os.listdir(LOCALES_DIR):
            if filename.endswith(".json"):
                lang_name = filename.replace(".json", "")
                with open(os.path.join(LOCALES_DIR, filename), "r", encoding="utf-8") as f:
                    languages[lang_name] = json.load(f)

    if not languages:
        languages = {"English": {"app_title": "Media Fixer", "lbl_no_file": "No file"}}

    available_languages = list(languages.keys())

    if os.path.exists(FLAGS_FILE):
        with open(FLAGS_FILE, "r", encoding="utf-8") as f:
            audio_flags = json.load(f)
    else:
        audio_flags = {"English": "eng"}

    available_flags = list(audio_flags.keys())

    current_config = {
        "ui_language": available_languages[0], 
        "default_audio_flag": available_flags[0]
    }

    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            current_config.update(json.load(f))

    texts = languages.get(current_config["ui_language"], languages.get("English", {}))

def save_config():
    with open(CONFIG_FILE, "w", encoding="utf-8") as f: 
        json.dump(current_config, f, indent=4)

init_config()