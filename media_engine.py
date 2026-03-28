import os
import platform
import shutil
import subprocess
import json
import urllib.request
import zipfile
import io
from config import BIN_DIR

FFMPEG_CMD = "ffmpeg"
FFPROBE_CMD = "ffprobe"

def update_ffmpeg_paths():
    global FFMPEG_CMD, FFPROBE_CMD
    if platform.system() == "Windows" and os.path.exists(os.path.join(BIN_DIR, "ffmpeg.exe")):
        FFMPEG_CMD = os.path.join(BIN_DIR, "ffmpeg.exe")
        FFPROBE_CMD = os.path.join(BIN_DIR, "ffprobe.exe")

def check_ffmpeg_installed():
    update_ffmpeg_paths()
    return shutil.which(FFMPEG_CMD) is not None and shutil.which(FFPROBE_CMD) is not None

def download_ffmpeg_windows(status_callback):
    url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    try:
        if not os.path.exists(BIN_DIR):
            os.makedirs(BIN_DIR)
        
        status_callback("Downloading FFmpeg... 0% ⏳")
        
        # Die Datei aufrufen
        req = urllib.request.urlopen(url)
        total_size = int(req.headers.get('content-length', 0))
        downloaded = 0
        chunk_size = 1024 * 1024  # 1 MB große "Häppchen"
        data = bytearray()
        
        # Stück für Stück herunterladen
        while True:
            chunk = req.read(chunk_size)
            if not chunk:
                break
            data.extend(chunk)
            downloaded += len(chunk)
            
            # Prozentzahl berechnen und ans UI schicken
            if total_size > 0:
                percent = int((downloaded / total_size) * 100)
                status_callback(f"Downloading FFmpeg... {percent}% ⏳")
        
        status_callback("Extracting files... 📦")
        
        # Die gesammelten Daten im RAM entpacken
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for file_info in z.infolist():
                if file_info.filename.endswith(("ffmpeg.exe", "ffprobe.exe")):
                    file_info.filename = os.path.basename(file_info.filename)
                    z.extract(file_info, BIN_DIR)
                    
        update_ffmpeg_paths()
        return True
        
    except Exception as e:
        print(f"Download error: {e}")
        return False

def probe_file(filepath):
    cmd = [FFPROBE_CMD, "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", "-select_streams", "a", filepath]
    
    # Der Ninja-Modus: Nur für Windows aktivieren!
    cflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, creationflags=cflags)
        return json.loads(result.stdout)
    except:
        return None