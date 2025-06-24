# G-Downloader Enhanced
![G-Downloader Logo](https://github.com/user-attachments/assets/77e47b81-ab0e-4735-8e79-2c04b09c00cc)
A modern, feature-rich media downloader for YouTube, Instagram, and TikTok with an advanced GUI interface and intelligent file management.

## Features

### 🎯 Core Features

- **Multi-platform support**: Download from YouTube, Instagram, and TikTok
- **Intelligent format detection**: Automatically detects and displays actual file formats (MP4, WEBM, MKV, etc.)
- **Quality selection**: Choose from 360p to 1080p for video downloads
- **Playlist support**: Download single videos or entire YouTube playlists
- **Comprehensive format support**: Handles 15+ video/audio formats including MP4, WEBM, MKV, AVI, MOV, FLV, MP3, M4A, AAC, and more

### 🖥️ Enhanced GUI Features

- **Wider main interface**: Spacious 1200x700 window optimized for better content viewing
- **Platform-specific tabs**: Organized interface with separate tabs for each platform showing actual downloaded formats
- **Interactive thumbnail previews**: Click to select entries, then hover for borderless video thumbnail previews
- **Two-quality thumbnail system**: Fast low-quality previews with background high-quality generation
- **System tray integration**: Completely silent startup - launches hidden to system tray
- **Auto-clipboard monitoring**: Automatically detect URLs from clipboard with platform switching
- **Real-time download progress**: Live progress updates and status notifications

### 🔧 Advanced Technical Features

- **Video thumbnail generation**: Extract actual thumbnails from video files using ffmpeg
- **Smart caching system**: Efficient thumbnail caching with progressive quality enhancement
- **Unicode support**: Full Arabic and special character support in filenames and titles
- **Auto-history management**: Automatic cleanup of deleted files and import of existing files
- **Background processing**: Downloads and thumbnail generation run in optimized background threads
- **Configuration persistence**: All settings automatically saved and restored between sessions

### 📁 Smart File Management

- **Format categorization**: Files automatically categorized by actual format (not requested format)
- **History tracking**: Complete download history with file status and thumbnail previews
- **Auto-import existing files**: Scans download directories and imports existing media files
- **Dead file cleanup**: Automatically removes entries for deleted files from history
- **Organized storage**: Downloads sorted by platform and actual file format

## Installation

### Prerequisites

1. **Python 3.7+** installed on your system
2. **yt-dlp** installed and accessible in PATH

### Install yt-dlp

```bash
# Using pip
pip install yt-dlp

# Or download from GitHub
# Visit: https://github.com/yt-dlp/yt-dlp#installation
```

### Install ffmpeg (Required for Video Thumbnails)

FFmpeg is essential for generating video thumbnails from local files:

```bash
# Windows (using Chocolatey)
choco install ffmpeg

# Windows (using Winget)
winget install FFmpeg

# macOS (using Homebrew)
brew install ffmpeg

# Linux (Ubuntu/Debian)
sudo apt install ffmpeg

# Linux (CentOS/RHEL)
sudo yum install ffmpeg

# Or download from: https://ffmpeg.org/download.html
```

### Install G-Downloader Enhanced

1. Clone or download this repository
2. Install required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Running the Application

```bash
python src/g-downloader.pyw
```

**Note**: The application starts completely hidden in the system tray for silent operation. Look for the G-Downloader icon in your system tray to access the main window.

### Main Interface

1. **System Tray Access**: Double-click the tray icon or right-click for menu options
2. **Settings Panel**: Configure save paths and enable/disable features like clipboard monitoring
3. **Platform Tabs**: Switch between YouTube, Instagram, and TikTok tabs with format-specific categorization
4. **Interactive History**: Click entries to select, then hover for instant video thumbnail previews
5. **Smart URL Input**: Paste URLs directly or let clipboard monitoring handle detection automatically

### Enhanced Thumbnail System

- **Click to Select**: Click any history entry to select it for thumbnail previews
- **Hover for Preview**: Hover over selected entries to see borderless video thumbnails
- **Two-Quality System**: Fast low-quality previews appear instantly, with high-quality versions generated in background
- **Video Frame Extraction**: Thumbnails generated directly from video files using ffmpeg
- **Smart Caching**: Intelligent caching system for optimal performance

### Download Process

1. **URL Detection**: Paste URLs or enable auto-monitoring for automatic detection
2. **Platform Switching**: Interface automatically switches to the appropriate platform tab
3. **Format Selection**: Choose format, quality, and playlist options (for YouTube)
4. **Live Preview**: See actual video thumbnails and information before downloading
5. **Progress Tracking**: Real-time download progress with background processing
6. **Auto-Categorization**: Files automatically sorted by actual format in history

### System Tray Features

- **Silent Startup**: Application launches completely hidden for unobtrusive operation
- **Tray Menu**: Right-click tray icon for quick access to show/hide and exit options
- **Smart Notifications**: Get notified when URLs are detected or downloads complete
- **Double-Click Access**: Double-click tray icon to show main window

## Configuration

### Default Save Path

- Customizable download location in settings
- Automatic directory creation with organized structure:
  ```
  Downloads/G-Downloader/
  ├── YouTube/
  │   ├── MP3/          # Audio files
  │   ├── MP4/          # Video files
  │   ├── WEBM/         # Alternative video format
  │   └── MKV/          # High-quality video format
  ├── Instagram/
  │   ├── MP4/          # Video content
  │   ├── JPG/          # Image content
  │   └── PNG/          # Image content
  └── TikTok/
      ├── MP4/          # Video content
      └── WEBM/         # Alternative format
  ```

### Advanced Features

- **Clipboard Monitoring**: Enable/disable automatic URL detection
- **Thumbnail Previews**: Toggle video thumbnail generation and hover previews
- **Format Detection**: Automatic detection and categorization of actual file formats
- **Unicode Support**: Full support for Arabic and special characters in filenames
- **Background Processing**: Optimized thumbnail generation and download management

## Supported Platforms & Formats

### YouTube

- **Video Formats**: MP4, WEBM, MKV, AVI, MOV, FLV, M4V
- **Audio Formats**: MP3, M4A, AAC, WAV, FLAC, OGG
- **Quality Options**: 360p, 480p, 720p, 1080p
- **Special Features**: Playlist support, format optimization, thumbnail extraction

### Instagram

- **Video Formats**: MP4, WEBM, MOV
- **Image Formats**: JPG, JPEG, PNG, GIF, WEBP
- **Features**: Story downloads, post downloads, automatic format detection

### TikTok

- **Video Formats**: MP4, WEBM, MOV
- **Features**: High-quality video downloads, format preservation

## Advanced Features

### Smart File Management

- **Auto-Import**: Automatically imports existing files from download directories
- **History Cleanup**: Removes entries for deleted files from history
- **Format Recognition**: Detects actual file formats vs. requested formats
- **Unicode Handling**: Proper support for international characters and Arabic text

### Thumbnail System

- **Video Frame Extraction**: Uses ffmpeg to extract actual frames from video files
- **Progressive Quality**: Low-quality for speed, high-quality for detail
- **Background Processing**: Non-blocking thumbnail generation
- **Smart Caching**: Efficient memory management and storage

### User Experience

- **Silent Operation**: Starts hidden in system tray
- **Platform Detection**: Automatic tab switching based on detected URLs
- **Click-to-Select**: Intuitive thumbnail preview interaction
- **Real-Time Updates**: Live status updates and progress tracking

## Troubleshooting

### Common Issues

1. **Application doesn't appear on startup**

   - The app now starts hidden in the system tray by design
   - Look for the G-Downloader icon in your system tray
   - Double-click the tray icon to show the main window

2. **No thumbnails showing**

   - Ensure ffmpeg is installed and accessible in PATH
   - Check that "Show thumbnails on hover" is enabled in settings
   - Click an entry first, then hover over it to see thumbnails

3. **yt-dlp not found**

   - Ensure yt-dlp is installed and in your system PATH
   - The application will prompt you to locate the executable if not found

4. **Download failures**

   - Check your internet connection
   - Verify the URL is accessible and not region-restricted
   - Some platforms may have temporary restrictions

5. **Format detection issues**

   - The app now shows actual file formats, not requested formats
   - If you requested MP4 but got WEBM, it will correctly show "WEBM"
   - This is normal behavior for format optimization

6. **Unicode/Arabic character issues**
   - The application now fully supports Arabic and special characters
   - Files with Arabic names should display and function correctly
   - Thumbnail generation works with international file names

### Performance Optimization

- **Thumbnail Generation**: Adjust quality settings in the code if needed
- **Memory Usage**: Clear thumbnail cache if memory usage becomes high
- **Background Processing**: Disable thumbnail preloading for slower systems

## Building Executable

### Using the Build Script

Use the provided build script for easy compilation:

```bash
# Build with default configuration
python build.py

# Build with specific configuration
python build.py optimized

# List available configurations
python build.py --list
```

### Manual Build

You can also build manually using PyInstaller:

```bash
# Install PyInstaller
pip install pyinstaller

# Build with default configuration
pyinstaller build-configs/g-downloader.spec

# Build with optimized configuration
pyinstaller build-configs/g-downloader-optimized.spec
```

### Available Build Configurations

- **default**: Standard build with all dependencies
- **optimized**: Smaller executable size, optimized for performance
- **embedded**: Single file with all resources embedded
- **final**: Production-ready build for distribution
- **complete**: Complete build with all features and compatibility

The built executable will be available in the `dist/` directory.

## Development

### Dependencies

- `tkinter`: GUI framework (built into Python)
- `Pillow`: Image processing for thumbnails
- `requests`: HTTP requests for web thumbnails
- `pystray`: System tray integration
- `yt-dlp`: Media downloading engine (external dependency)
- `ffmpeg`: Video processing for thumbnail generation (external dependency)

### File Structure

```
g-downloader/
├── src/
│   └── g-downloader.pyw        # Main application with all features
├── assets/
│   └── icon.ico               # Application icon for tray and window
├── requirements.txt           # Python dependencies
├── README.md                  # This comprehensive documentation
├── .gitignore                # Git ignore patterns
└── .g-downloader-config.json  # User configuration (auto-created)
```

### Key Features Implementation

- **Silent Startup**: `self.root.withdraw()` called immediately after window creation
- **Format Detection**: `get_file_format_from_extension()` function for accurate format identification
- **Thumbnail System**: Progressive quality system with background generation
- **Unicode Support**: Safe printing and encoding throughout the application
- **Click-to-Select**: `selected_entry_id` tracking for targeted thumbnail previews

## License

This project is open source. Feel free to modify and distribute according to your needs.

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

### Recent Major Updates

- ✅ **Silent Startup**: Application now launches completely hidden to system tray
- ✅ **Smart Format Detection**: Shows actual file formats (WEBM, MKV, etc.) instead of requested
- ✅ **Enhanced Thumbnails**: Click-to-select system with borderless previews
- ✅ **Unicode Support**: Full Arabic and special character support
- ✅ **Wider Interface**: Optimized 1200x700 layout for better content viewing
- ✅ **Progressive Thumbnails**: Two-quality system for optimal performance
- ✅ **Background Processing**: Non-blocking thumbnail generation and downloads
