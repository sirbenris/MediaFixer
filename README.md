🎬 MediaFixer
MediaFixer is a powerful, user-friendly tool designed to clean up and standardize your media library. It automatically fixes audio streams, removes unwanted metadata, and ensures your files are compatible with all modern players.

!

✨ Key Features
Automated FFmpeg Setup: No manual installation required. The built-in Setup Wizard handles everything for you.

Multi-Platform Support: Native builds for Windows (ZIP) and Linux.

Batch Processing: Fix entire folders of movies or TV shows at once.

Smart Metadata Filtering: Cleans title tags and unwanted stream information.

Non-Destructive: Uses a simulation mode to show you changes before they happen.

Multilingual: Supports English and German (automatically detects system language).

🚀 Installation & Usage
Windows (Recommended)
Go to the Releases page.

Download MediaFixer-windows.zip.

Right-click the ZIP file and select "Extract All...".

Open the folder and run MediaFixer-windows.exe.

Follow the Setup Wizard to download FFmpeg automatically.

Linux
Download the MediaFixer-linux binary from the Releases page.

Give it execution permissions:

Bash
chmod +x MediaFixer-linux
Run it: ./MediaFixer-linux

🛠 For Developers
If you want to run the code from source:

Clone the repository:

Bash
git clone https://github.com/benris/MediaFixer.git
cd MediaFixer
Create a virtual environment:

Bash
python -m venv .venv
source .venv/bin/activate  # Linux
.\.venv\Scripts\activate   # Windows
Install dependencies:

Bash
pip install customtkinter
Run the app:

Bash
python main.py
🛡️ Antivirus Note (Windows)
Since this executable is not digitally signed, Windows Defender or Edge might flag it as "unrecognized". This is a common issue with Python-based tools. You can safely click "Run anyway" or "Keep file". The source code is fully open for inspection.