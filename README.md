# 🎬 Media Fixer

A powerful and modular desktop application to analyze and repair audio streams in MP4 and MKV files. Built with Python and CustomTkinter.

## ✨ Key Features
- **Batch Processing:** Fix entire folders or seasons at once.
- **Simulation Mode:** Professional dry-run preview before touching any file.
- **Smart Filtering:** Isolate files by language flags, codecs, or bitrates.
- **Auto-Download:** Installs FFmpeg automatically for Windows users.
- **Safety First:** Includes `.orig` backups.

## 🚀 Setup & Run
1. `git clone https://github.com/benris/MediaFixer.git`
2. `pip install customtkinter`
3. `python main.py`

## OR DOWNLOAD AT RELEASES PAGE (https://github.com/sirbenris/MediaFixer/releases)

## 📦 Running the Pre-built Binary (Linux)

If you downloaded the standalone version from the [Releases](https://github.com/sirbenris/MediaFixer/releases) page, you might need to give it execution permissions first:

### Option 1: Using the Terminal (Recommended)
1. Open your terminal in the download folder.
2. Make the file executable:
   chmod +x MediaFixer
3. Run it:
   ./MediaFixer

### Option 2: Using the GUI
1. Right-click the MediaFixer file.
2. Select Properties.
3. Go to the Permissions tab.
4. Check the box "Allow executing file as program".
5. Close and double-click the file to launch.

"Note: Some Antivirus engines might flag the EXE as a false positive due to the PyInstaller packaging. This is a known issue with non-signed Python executables."

## ⚖️ License
MIT - Built by Benris