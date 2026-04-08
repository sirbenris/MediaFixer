# 🎬 MediaFixer

![Downloads](https://img.shields.io/github/downloads/sirbenris/MediaFixer/total?style=for-the-badge&color=005FB8)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey?style=for-the-badge)
![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)

**English** | [Deutsch](README.de.md)

**MediaFixer** is a lightweight, zero-configuration desktop tool designed to clean up your media library's audiotracks before it hits your server (like Plex, Jellyfin, or Emby). 

If you are tired of seeing "Unknown" audio tracks, dealing with incompatible audio codecs causing unexpected transcoding, or finding weird encoder artifacts in your track titles, this tool is built for you.

## ✨ Key Features

* **Bulk Audio Patching:** Convert all audio tracks in a folder to a specific codec (e.g., AC3, AAC), change bitrates, or force a stereo downmix for maximum compatibility.
* **Fix Language Flags:** Batch-apply the correct language tags (English, German, etc.) so your media player automatically selects the right audio track.
* **Metadata Scrubbing:** Easily rename track titles or completely clear out hidden data-trash like `handler_name` tags left behind by encoders.
* **Safe Simulation Mode:** Never ruin your library. MediaFixer offers a simulation mode that previews every single planned change in a detailed log before a single byte is written to your drive.
* **Zero Config Setup:** No need to mess with terminal commands or manually download FFmpeg. The built-in setup wizard handles everything for you on the first launch.
* **Modern UI:** Built with an intuitive, dark-mode GUI (Rime Theme) that supports both English and German natively.

---

## 🚀 Installation & Usage

### 🪟 Windows (Recommended)
1. Go to the [Releases page](../../releases/latest).
2. Download the latest `MediaFixer-windows.zip`.
3. Extract the ZIP file into a folder of your choice.
4. Run `MediaFixer-windows.exe`. 
5. *Note: On the first launch, the setup wizard will automatically download the required FFmpeg binaries into the folder.*

### 🐧 Linux
1. Go to the [Releases page](../../releases/latest).
2. Download the `MediaFixer-linux` binary.
3. Open your terminal and give it execution permissions:

       chmod +x MediaFixer-linux

4. Run the application:

       ./MediaFixer-linux

5. *Note: Please ensure `ffmpeg` is installed on your system (e.g., `sudo apt install ffmpeg`).*

---

## 🛠 For Developers (Running from Source)

Want to tweak the code or build it yourself? No problem!

1. Clone the repository:

       git clone https://github.com/sirbenris/MediaFixer.git
       cd MediaFixer

2. Create and activate a virtual environment:

       python -m venv .venv
       source .venv/bin/activate  # On Linux
       .\.venv\Scripts\activate   # On Windows

3. Install the required dependencies:

       pip install customtkinter pymediainfo

4. Run the app:

       python main.py

---

## 🛡️ Important Notes & Legal

### Antivirus False Positives (Windows)
Because this application is compiled using `PyInstaller` and is not digitally signed with an expensive enterprise certificate, Windows Defender or your browser might flag the `.exe` file as "unrecognized" or potentially unsafe. **This is a known, common false positive for Python-based standalone executables.** You can safely click *More info -> Run anyway*. The complete source code is available here for inspection.

### Third-Party Acknowledgments
* **FFmpeg:** This software uses code of [FFmpeg](http://ffmpeg.org) licensed under the LGPLv2.1 and its source can be downloaded from their website.
* **MediaInfo:** This software utilizes `pymediainfo` and the `MediaInfo` library (licensed under the BSD-2-Clause license) for robust metadata extraction.

### Disclaimer
*This tool modifies media files. While it includes a backup option and a simulation mode, the software is provided "as is", without warranty of any kind. Always ensure you have backups of your critical media files before performing bulk operations.*