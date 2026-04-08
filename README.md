# 🎬 MediaFixer

![Downloads](https://img.shields.io/github/downloads/sirbenris/MediaFixer/total?style=for-the-badge&color=005FB8)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey?style=for-the-badge)
![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)

**MediaFixer** is a lightweight, zero-configuration desktop tool designed to clean up your media library before it hits your server (like Plex, Jellyfin, or Emby). 

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
   ```bash
   chmod +x MediaFixer-linux