<h1 align="center">g-downloader</h1 align="center">

![ChatGPT Image May 9, 2025, 01_04_27 AM](https://github.com/user-attachments/assets/77e47b81-ab0e-4735-8e79-2c04b09c00cc)

A clipboard monitor utility that detects and downloads media from YouTube, Instagram, and TikTok links.

## Features

- **Automatic link detection**: Monitors your clipboard for supported media links
- **Multiple platforms supported**: YouTube, Instagram, and TikTok
- **YouTube options**:
  - Download as MP3 or MP4
  - Select video resolution (1080p, 720p, 480p, 360p)
  - Download single videos or entire playlists
- **Organized downloads**: Files are saved in categorized folders within your Downloads directory
- **Background operation**: Runs silently in the background monitoring clipboard
- **Playlist support**: Automatically detects YouTube playlists
- **Multi-platform media**: Works with YouTube videos, TikTok videos, Instagram reels and videos

## Requirements

- Python 3.7+ (if running from source)
- Tkinter (included with Python on Windows/macOS, may need separate installation on Linux)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp#installation) (automatically detected or can be manually located)

## Installation

### Pre-built Executable

1. Download `g-downloader-0.1.exe` from the latest release
2. Run the executable to start the application
3. No installation needed - the application will run in the background

### From Source

#### Clone the Repository

```bash
git clone https://github.com/ghassanelgendy/g-downloader.git
cd g-downloader
```

#### Install Requirements

```bash
# Install yt-dlp
pip install yt-dlp

# On Linux, you might need to install tkinter separately
# For Debian/Ubuntu:
sudo apt-get install python3-tk
# For Fedora:
sudo dnf install python3-tkinter
# For Arch Linux:
sudo pacman -S tk
```

#### Run the Application

```bash
python g-downloader.pyw
```

### Building from Source

To create your own executable:

```bash
# Install PyInstaller
pip install pyinstaller

# Create the executable
pyinstaller --noconsole --onefile  g-downloader g-downloader.pyw
```

## Autostart with Windows

To make g-downloader start automatically with Windows:

1. Press `Win+R` and type `shell:startup`
2. Create a shortcut to `g-downloader-0.1.exe` in this folder
3. The application will now start automatically when you log in

## Usage

1. Copy a YouTube, Instagram, or TikTok URL to your clipboard
2. A prompt window will appear with download options
3. Select your preferred format and options
4. Click "Download" to start the download

Downloaded files will be saved to:

- YouTube videos: `~/Downloads/g-downloader/YouTube/MP4/`
- YouTube audio: `~/Downloads/g-downloader/YouTube/MP3/`
- Instagram content: `~/Downloads/g-downloader/Instagram/`
- TikTok videos: `~/Downloads/g-downloader/TikTok/`

## Stopping the Application

The application runs in the background. To stop it, use Task Manager to end the process.

## Technical Details

### Architecture

g-downloader is a Python application that:

1. Runs as a background process without a visible window (.pyw)
2. Uses Tkinter for GUI popups
3. Monitors clipboard content
4. Detects and validates media URLs
5. Downloads content using yt-dlp

### Implementation Details

#### Clipboard Monitoring

The application uses PowerShell's `Get-Clipboard` command to access the Windows clipboard through a subprocess call. This method allows continuous monitoring without requiring specialized libraries.

#### URL Detection

URL detection is performed using regular expressions:

- YouTube: Matches domains `youtube.com` and `youtu.be`
- Instagram: Matches domains `instagram.com` and `instagr.am`
- TikTok: Matches domains `tiktok.com` and `vm.tiktok.com`

#### Threading Model

The application uses multiple threads:

- Main thread: Runs Tkinter event loop
- Monitor thread: Continuously checks clipboard
- Download thread: Spawned for each download to maintain UI responsiveness

#### Download Process

The application uses yt-dlp, a powerful YouTube-DL fork with enhanced features:

1. For YouTube:

   - MP4 downloads use format selection based on user-chosen resolution
   - MP3 downloads extract audio from best available source
   - Playlist handling depends on user selection

2. For Instagram and TikTok:
   - Uses "best" format selection to get highest quality

#### Directory Structure

Downloads are organized into the following structure:

```
~/Downloads/g-downloader/
├── YouTube/
│   ├── MP3/
│   └── MP4/
├── Instagram/
└── TikTok/
```

### Build Process

#### PyInstaller Configuration

The application is built using PyInstaller with the following configuration:

```
pyinstaller --name=g-downloader --onefile --windowed --icon=icon.ico g-downloader.pyw
```

Key settings:

- `--onefile`: Creates a single executable file
- `--windowed`: Prevents console window from appearing
- `--icon`: Sets the application icon

#### Dependencies

The following dependencies are included in the build:

- Python standard library
- Tkinter
- yt-dlp (detected at runtime)

## License

MIT License

Copyright (c) 2025
