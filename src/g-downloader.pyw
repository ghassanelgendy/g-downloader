import os
import time
import re
import threading
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import sys
import shutil
import json
import requests
from PIL import Image, ImageTk
import io
import pystray


# --- Application Root Directory ---
APP_ROOT = Path(__file__).parent.parent  # Go up from src/ to main directory
DATA_DIR = APP_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)  # Create data directory if it doesn't exist

# --- History Management ---
HISTORY_FILE = DATA_DIR / "history.json"


def safe_log(message):
    """Safely print messages that might contain Unicode characters"""
    try:
        print(message)
    except UnicodeEncodeError:
        # Extract the safe parts and replace problematic characters
        safe_message = message.encode("ascii", "replace").decode("ascii")
        print(safe_message)


def log(message):
    """Log message only if logging is enabled"""
    if config.get("logging_enabled", False):
        import datetime

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"

        # Add to buffer
        log_buffer.append(log_entry)

        # Keep buffer size manageable
        if len(log_buffer) > MAX_LOG_ENTRIES:
            log_buffer.pop(0)  # Remove oldest entry

        # Also print to console for immediate debugging
        safe_log(log_entry)


def get_file_format_from_extension(file_path):
    """Detect the actual file format from the file extension"""
    if not file_path:
        return "Unknown"

    path_obj = Path(file_path)
    extension = path_obj.suffix.lower()

    # Map extensions to display formats
    format_mapping = {
        ".mp4": "MP4",
        ".webm": "WEBM",
        ".mkv": "MKV",
        ".avi": "AVI",
        ".mov": "MOV",
        ".flv": "FLV",
        ".m4v": "M4V",
        ".3gp": "3GP",
        ".mp3": "MP3",
        ".m4a": "M4A",
        ".aac": "AAC",
        ".wav": "WAV",
        ".flac": "FLAC",
        ".ogg": "OGG",
        ".jpg": "JPG",
        ".jpeg": "JPEG",
        ".png": "PNG",
        ".gif": "GIF",
        ".webp": "WEBP",
    }

    return format_mapping.get(
        extension, extension.upper().replace(".", "") if extension else "Unknown"
    )


def load_history():
    """Load download history from the JSON file."""
    if not HISTORY_FILE.exists():
        return []
    try:
        with HISTORY_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []  # Return empty list if file is corrupted or unreadable


def save_history(history):
    """Save the download history to the JSON file."""
    try:
        with HISTORY_FILE.open("w", encoding="utf-8") as f:
            json.dump(history, f, indent=4)
    except IOError as e:
        log(f"Error saving history: {e}")


def add_to_history(entry):
    """Add a new entry to the history, avoiding duplicates."""
    history = load_history()
    # Prevent duplicates by checking for the same file path
    is_duplicate = any(h.get("file_path") == entry.get("file_path") for h in history)
    if not is_duplicate:
        history.insert(0, entry)  # Add new items to the top
        save_history(history)


# Function to find yt-dlp executable
def find_ytdlp():
    # First, check if yt-dlp is in PATH
    ytdlp_cmd = "yt-dlp.exe" if sys.platform == "win32" else "yt-dlp"
    ytdlp_path = shutil.which(ytdlp_cmd)
    if ytdlp_path:
        return ytdlp_path

    # Platform-specific checks
    if sys.platform == "win32":
        # Try Python Scripts folders for Windows
        for python_version in [
            "Python311",
            "Python310",
            "Python39",
            "Python38",
            "Python37",
        ]:
            # Check standard Python installation
            candidate = Path(
                os.path.expanduser(
                    f"~\\AppData\\Local\\Programs\\Python\\{python_version}\\Scripts\\yt-dlp.exe"
                )
            )
            if candidate.exists():
                return str(candidate)

            # Check Windows Store Python installation
            candidate = Path(
                os.path.expanduser(
                    f"~\\AppData\\Local\\Packages\\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\\LocalCache\\local-packages\\{python_version}\\Scripts\\yt-dlp.exe"
                )
            )
            if candidate.exists():
                return str(candidate)

    if sys.platform in ["linux", "darwin"]:
        common_paths = [
            "/usr/local/bin/yt-dlp",
            "/usr/bin/yt-dlp",
            f"{os.path.expanduser('~')}/.local/bin/yt-dlp",
        ]
        for path in common_paths:
            if Path(path).exists():
                return path

    # If not found automatically, ask user to locate it
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    messagebox.showinfo(
        "yt-dlp Not Found",
        "Could not find yt-dlp automatically. Please locate the yt-dlp executable on your system.\n\n"
        "If you don't have yt-dlp installed, please install it first from: https://github.com/yt-dlp/yt-dlp#installation",
    )
    file_path = filedialog.askopenfilename(
        title="Select yt-dlp executable",
        filetypes=(
            [("Executable files", "*.exe"), ("All files", "*.*")]
            if sys.platform == "win32"
            else [("All files", "*")]
        ),
    )
    root.destroy()

    if file_path and Path(file_path).exists():
        return file_path
    return None


# Get the yt-dlp path at startup
YTDLP_PATH = find_ytdlp()

CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

# Configuration file path
CONFIG_FILE = DATA_DIR / "config.json"

# Default configuration - downloads in user's Downloads folder
DOWNLOADS_DIR = Path.home() / "Downloads" / "G-Downloader"
DEFAULT_CONFIG = {
    "base_dir": str(DOWNLOADS_DIR),
    "yt_mp3_dir": str(DOWNLOADS_DIR / "YouTube" / "MP3"),
    "yt_mp4_dir": str(DOWNLOADS_DIR / "YouTube" / "MP4"),
    "insta_dir": str(DOWNLOADS_DIR / "Instagram"),
    "tiktok_dir": str(DOWNLOADS_DIR / "TikTok"),
    "auto_monitor": True,
    "notifications_enabled": True,
    "show_thumbnails": False,
    "logging_enabled": False,
}


def load_config():
    """Load configuration from file or create default"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                # Ensure all required keys exist
                for key, value in DEFAULT_CONFIG.items():
                    if key not in config:
                        config[key] = value
                return config
        except Exception as e:
            log(f"Error loading config: {e}")
            return DEFAULT_CONFIG.copy()
    else:
        return DEFAULT_CONFIG.copy()


def save_config(config):
    """Save configuration to file"""
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        log(f"Error saving config: {e}")


# Load configuration
config = load_config()

# Log buffer to store log messages
log_buffer = []
MAX_LOG_ENTRIES = 1000  # Limit log entries to prevent memory issues


# Create directories based on config
def create_directories():
    """Create download directories based on configuration"""
    try:
        for folder_path in [
            config["yt_mp3_dir"],
            config["yt_mp4_dir"],
            config["insta_dir"],
            config["tiktok_dir"],
        ]:
            Path(folder_path).mkdir(parents=True, exist_ok=True)
    except Exception as e:
        log(f"Error creating directories: {e}")


create_directories()


def is_youtube_playlist(url):
    # Simple check, might need refinement for edge cases
    return url and "list=" in url


# Regex helpers
def is_youtube_url(text):
    return (
        text
        and re.match(r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/\S+", text)
        is not None
    )


def is_instagram_url(text):
    return (
        text
        and re.match(r"(https?://)?(www\.)?(instagram\.com|instagr\.am)/\S+", text)
        is not None
    )


def is_tiktok_url(text):
    return (
        text
        and re.match(
            r"(https?://)?(www\.)?(tiktok\.com|vm\.tiktok\.com)/(@[^/]+/video/\d+|\w+/\S+)",
            text,
        )
        is not None
    )


def get_video_info(url, platform):
    """Get video information including thumbnail"""
    try:
        if not Path(YTDLP_PATH).exists():
            return None

        cmd = [YTDLP_PATH, "--dump-json", "--no-playlist", url]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            creationflags=CREATE_NO_WINDOW,
        )

        if result.returncode == 0:
            import json

            info = json.loads(result.stdout)
            return {
                "title": info.get("title", "Unknown Title"),
                "thumbnail": info.get("thumbnail", ""),
                "duration": info.get("duration", 0),
                "uploader": info.get("uploader", "Unknown"),
                "view_count": info.get("view_count", 0),
            }
    except Exception as e:
        log(f"Error getting video info: {e}")
    return None


def generate_video_thumbnail(video_path, max_size=(200, 150), quality="high"):
    """Generate thumbnail from video file using ffmpeg"""
    try:
        video_path = Path(video_path)
        if not video_path.exists():
            log(f"Debug: Video file not found: {video_path}")
            return None

        # Only generate thumbnails for video files
        if video_path.suffix.lower() not in [
            ".mp4",
            ".webm",
            ".avi",
            ".mkv",
            ".mov",
            ".flv",
            ".m4v",
            ".3gp",
        ]:
            log(f"Debug: Not a video file: {video_path}")
            return None

        # Check if ffmpeg is available
        ffmpeg_cmd = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
        if not shutil.which(ffmpeg_cmd):
            log("Debug: ffmpeg not found, cannot generate video thumbnail")
            log("Debug: Install ffmpeg to enable video thumbnail generation")
            return None

        # Create a temporary file for the thumbnail
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
            temp_thumb_path = tmp_file.name

        # Quality settings based on mode
        if quality == "low":
            # Ultra fast, extremely low quality for batch processing
            quality_value = "15"  # Extremely low quality for maximum speed
            seek_time = "0.1"  # Minimal seek time
        else:
            # High quality for on-demand generation
            quality_value = "2"  # High quality
            seek_time = "1"  # Standard seek time

        # Extract frame at specified time
        # Handle Unicode file paths properly for Arabic and other special characters
        video_path_str = str(video_path)

        cmd = [
            ffmpeg_cmd,
            "-i",
            video_path_str,
            "-ss",
            seek_time,  # Seek time based on quality
            "-vframes",
            "1",  # Extract 1 frame
            "-q:v",
            quality_value,  # Quality based on mode
            "-f",
            "mjpeg",  # Force MJPEG format for speed
            "-y",  # Overwrite output file
            temp_thumb_path,
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            creationflags=CREATE_NO_WINDOW,
            encoding="utf-8",
            errors="ignore",  # Ignore encoding errors to handle Arabic/special characters
        )

        if result.returncode == 0 and Path(temp_thumb_path).exists():
            # Load and resize the generated thumbnail
            img = Image.open(temp_thumb_path)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)

            # Clean up temp file
            Path(temp_thumb_path).unlink(missing_ok=True)

            quality_text = "low quality" if quality == "low" else "high quality"
            log(
                f"Debug: Successfully generated {quality_text} thumbnail from: {video_path.name}"
            )
            return photo
        else:
            log(f"Debug: Failed to generate thumbnail from: {video_path.name}")
            # Clean up temp file if it exists
            Path(temp_thumb_path).unlink(missing_ok=True)

    except Exception as e:
        log(f"Error generating video thumbnail: {e}")

    return None


def download_thumbnail(url, max_size=(200, 150)):
    """Download and resize thumbnail from URL (fallback for web thumbnails)"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        response = requests.get(url, timeout=15, headers=headers)

        if response.status_code == 200:
            img = Image.open(io.BytesIO(response.content))
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            log(f"Debug: Successfully loaded thumbnail from: {url}")
            return photo
        else:
            log(f"Debug: Failed to load thumbnail - HTTP {response.status_code}")
    except Exception as e:
        log(f"Error downloading thumbnail: {e}")
    return None


# Download logic
def download_media(url, platform, format_choice="MP4", resolution=None, callback=None):
    log(f"Starting download for: {url}")
    cmd = []
    try:
        if not Path(YTDLP_PATH).exists():
            log(f"Error: yt-dlp not found at {YTDLP_PATH}")
            if callback:
                callback(f"Error: yt-dlp not found", "error")
            return

        if platform == "YouTube":
            if format_choice == "MP3":
                output_template = str(
                    Path(config["yt_mp3_dir"]) / "%(title).80s.%(ext)s"
                )
                cmd = [
                    YTDLP_PATH,
                    "-f",
                    "bestaudio",
                    "--extract-audio",
                    "--audio-format",
                    "mp3",
                    "-o",
                    output_template,
                    url,
                ]
            else:  # MP4
                output_template = str(
                    Path(config["yt_mp4_dir"]) / "%(title).80s.%(ext)s"
                )
                res_option = resolution if resolution else "720"
                format_string = f"bestvideo[ext=mp4][height<={res_option}]+bestaudio[ext=m4a]/best[ext=mp4]/best"
                cmd = [YTDLP_PATH, "-f", format_string, "-o", output_template, url]

        elif platform == "Instagram":
            output_template = str(Path(config["insta_dir"]) / "%(title).80s.%(ext)s")
            cmd = [YTDLP_PATH, "-f", "best", "-o", output_template, url]

        elif platform == "TikTok":
            output_template = str(Path(config["tiktok_dir"]) / "%(title).80s.%(ext)s")
            cmd = [
                YTDLP_PATH,
                "--no-check-certificates",
                "--no-warnings",
                "-f",
                "best",
                "-o",
                output_template,
                url,
            ]

        else:
            log(f"Unsupported platform: {platform}")
            if callback:
                callback(f"Unsupported platform: {platform}", "error")
            return

        log(f"Executing command: {' '.join(cmd)}")

        if callback:
            callback("Downloading...", "info")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            creationflags=CREATE_NO_WINDOW,
        )

        if result.returncode == 0:
            log(f"Download successful: {url}")

            # --- Log to history ---
            info = get_video_info(url, platform)
            title = info["title"] if info and "title" in info else "Unknown Title"
            thumbnail_url = info.get("thumbnail", "") if info else ""

            # Try to extract the final filename from yt-dlp's output
            output_str = result.stdout
            file_path = None

            # Define markers for different output types
            destination_markers = [
                "[ExtractAudio] Destination: ",
                '[Merger] Merging formats into "',
                "[download] Destination: ",
            ]

            for line in output_str.splitlines():
                for marker in destination_markers:
                    if marker in line:
                        # Extract the path and clean it up
                        file_path = line.split(marker)[1].strip().replace('"', "")
                        break
                if file_path:
                    break

            if file_path and Path(file_path).exists():
                # Detect actual file format from the downloaded file
                actual_format = get_file_format_from_extension(file_path)

                entry = {
                    "platform": platform,
                    "title": title,
                    "url": url,
                    "format": actual_format,  # Use actual file format instead of requested format
                    "file_path": file_path,
                    "timestamp": time.time(),
                    "thumbnail_url": thumbnail_url,  # Store thumbnail URL
                }
                add_to_history(entry)
            # --- End log to history ---

            if callback:
                callback("Download completed successfully!", "success")
        else:
            log(f"Download failed for {url}. Return code: {result.returncode}")
            log(f"stderr: {result.stderr}")
            if callback:
                callback(f"Download failed: {result.stderr}", "error")

    except Exception as e:
        log(f"An error occurred during download_media for {url}: {e}")
        if callback:
            callback(f"Error: {str(e)}", "error")


# Function to center the window
def center_window(window, width, height):
    # Ensure window exists and calculations are valid
    try:
        window.update_idletasks()  # Update geometry info
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        if screen_width > 0 and screen_height > 0 and width > 0 and height > 0:
            x_position = int(screen_width / 2 - width / 2)
            y_position = int(screen_height / 2 - height / 2)
            # Clamp positions to be on screen
            x_position = max(0, x_position)
            y_position = max(0, y_position)
            window.geometry(f"{width}x{height}+{x_position}+{y_position}")
        else:
            log("Warning: Could not get valid screen/window dimensions for centering.")
    except Exception as e:
        log(f"Error centering window: {e}")


# GUI Prompt
def prompt_download(url, platform):
    try:

        def proceed():
            try:
                format_choice = format_var.get()
                resolution = res_var.get() if format_choice == "MP4" else None
                is_playlist = is_youtube_playlist(url)
                full_playlist = (
                    playlist_var.get() == "Full playlist" if is_playlist else False
                )

                popup.destroy()  # Destroy the popup window

                final_url = url
                # Modify URL only if it's a playlist and user chose single video
                if platform == "YouTube" and is_playlist and not full_playlist:
                    # Simple split, might fail on complex URLs, but ok for common cases
                    url_parts = url.split("&list=")
                    if len(url_parts) > 0:
                        final_url = url_parts[0]

                log(
                    f"Proceeding to download: {final_url}, Format: {format_choice}, Res: {resolution}"
                )  # Won't show in pyw

                # Start download in a separate thread to keep GUI responsive
                threading.Thread(
                    target=download_media,
                    args=(final_url, platform, format_choice, resolution),
                    daemon=True,  # Allows program to exit even if thread is running
                ).start()
            except Exception as e:
                log(f"Error in proceed function: {e}")
                # Maybe show tk.messagebox error
                try:  # Ensure popup exists before trying to destroy
                    if popup and popup.winfo_exists():
                        popup.destroy()
                except:
                    pass

        # Use Toplevel for secondary windows if a root might exist
        # If this is the *only* window, tk.Tk() is okay, but Toplevel is safer practice
        popup = tk.Toplevel()
        popup.title("g-downloader")

        # Prevent user from interacting with other windows (if any)
        popup.grab_set()
        # Make sure focus is on this window
        popup.focus_set()

        # Display the detected link
        tk.Label(
            popup,
            text=f"{platform} link detected:\n{url}",
            wraplength=380,
            justify="left",
        ).pack(pady=10, padx=10)

        format_var = tk.StringVar(value="MP4")
        res_var = tk.StringVar(value="720")  # Default resolution
        playlist_var = tk.StringVar(value="Single video")  # Default playlist option

        if platform == "YouTube":
            options_frame = tk.Frame(popup)  # Group options

            # --- Playlist Options (only if playlist detected) ---
            if is_youtube_playlist(url):
                pl_frame = tk.LabelFrame(options_frame, text="Playlist Options")
                tk.Radiobutton(
                    pl_frame,
                    text="Download only this video",
                    variable=playlist_var,
                    value="Single video",
                ).pack(anchor="w", padx=5)
                tk.Radiobutton(
                    pl_frame,
                    text="Download entire playlist",
                    variable=playlist_var,
                    value="Full playlist",
                ).pack(anchor="w", padx=5)
                pl_frame.pack(pady=5, padx=10, fill="x")

            # --- Format Options ---
            fmt_frame = tk.LabelFrame(options_frame, text="Format")
            tk.Radiobutton(
                fmt_frame, text="Video (MP4)", variable=format_var, value="MP4"
            ).pack(anchor="w", padx=5)
            tk.Radiobutton(
                fmt_frame, text="Audio (MP3)", variable=format_var, value="MP3"
            ).pack(anchor="w", padx=5)
            fmt_frame.pack(pady=5, padx=10, fill="x")

            # --- Resolution Options (only relevant for MP4) ---
            res_frame = tk.LabelFrame(options_frame, text="Resolution (for MP4)")
            # Set default resolution
            res_var.set("720")
            for res in ["1080", "720", "480", "360"]:
                tk.Radiobutton(
                    res_frame, text=res + "p", variable=res_var, value=res
                ).pack(anchor="w", padx=5)
            res_frame.pack(pady=5, padx=10, fill="x")

            options_frame.pack(fill="x")

        elif platform == "Instagram":
            # Instagram only needs confirmation, defaults to MP4 implicitly via download_media
            tk.Label(popup, text="Instagram content will be downloaded.").pack(pady=10)
            format_var.set("MP4")  # Set conceptually, download logic handles it

        elif platform == "TikTok":
            # TikTok only needs confirmation, defaults to MP4
            tk.Label(popup, text="TikTok content will be downloaded.").pack(pady=10)
            format_var.set("MP4")  # Set conceptually, download logic handles it

        # --- Download Button ---
        tk.Button(popup, text="Download", command=proceed).pack(pady=15)

        # --- Centering ---
        # Calculate dynamic height after packing widgets
        popup.update_idletasks()  # Ensure widgets are placed and sized
        width = 400  # Fixed width
        height = popup.winfo_reqheight() + 20  # Required height + padding
        center_window(popup, width, height)

        # Don't call mainloop on Toplevel if a root mainloop is running/will run
        # popup.mainloop() # This would block if called on Toplevel

    except Exception as e:
        log(f"Error creating prompt window: {e}")


# Clipboard watcher using Windows clipboard directly
def clipboard_monitor():
    last_text = ""
    try:
        last_text = get_clipboard_text()  # Get initial state
    except Exception as e:
        log(f"Error getting initial clipboard content: {e}")
        # Decide whether to continue or exit if clipboard is inaccessible
        # return

    processed_urls = set()  # Keep track of processed URLs to avoid repeats

    log("Clipboard monitor started...")
    while True:
        try:
            current_text = get_clipboard_text()
            # Check if text changed, is not empty, and hasn't been processed
            if (
                current_text
                and current_text != last_text
                and current_text not in processed_urls
            ):
                log(f"Clipboard changed: {current_text[:50]}...")
                url_to_process = None
                platform = None

                if is_youtube_url(current_text):
                    url_to_process = current_text
                    platform = "YouTube"
                elif is_instagram_url(current_text):
                    url_to_process = current_text
                    platform = "Instagram"
                elif is_tiktok_url(current_text):
                    url_to_process = current_text
                    platform = "TikTok"

                if url_to_process:
                    log(f"Detected {platform} URL: {url_to_process}")
                    # Run the GUI prompt. It handles its own threading for download.
                    prompt_download(url_to_process, platform)
                    processed_urls.add(url_to_process)  # Mark as processed

                last_text = (
                    current_text  # Update last_text only after processing change
                )

            # Prevent busy-waiting
            time.sleep(1)  # Check every second

        except KeyboardInterrupt:
            log("Clipboard monitor interrupted.")
            break
        except Exception as e:
            # Log error and continue monitoring if possible
            log(f"Error in clipboard monitoring loop: {e}")
            # Avoid spamming errors if clipboard access is consistently failing
            time.sleep(5)


def show_log_viewer():
    """Show log viewer window"""
    log_window = tk.Toplevel()
    log_window.title("Debug Logs")
    log_window.geometry("800x600")
    log_window.resizable(True, True)

    # Center the window
    center_window(log_window, 800, 600)

    # Main frame
    main_frame = ttk.Frame(log_window)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # Info label
    info_label = ttk.Label(
        main_frame,
        text=f"Debug Logs ({len(log_buffer)} entries) - Logging: {'ON' if config.get('logging_enabled', False) else 'OFF'}",
    )
    info_label.pack(pady=(0, 10))

    # Text widget with scrollbar
    text_frame = ttk.Frame(main_frame)
    text_frame.pack(fill=tk.BOTH, expand=True)

    # Text widget
    text_widget = tk.Text(
        text_frame, wrap=tk.WORD, font=("Courier", 9), bg="white", fg="black"
    )

    # Scrollbar
    scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
    text_widget.configure(yscrollcommand=scrollbar.set)

    # Pack text widget and scrollbar
    text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # Populate with log entries
    if log_buffer:
        for entry in log_buffer:
            text_widget.insert(tk.END, entry + "\n")
    else:
        text_widget.insert(
            tk.END,
            "No log entries available.\nEnable logging to see debug messages here.",
        )

    # Make text widget read-only
    text_widget.config(state=tk.DISABLED)

    # Auto-scroll to bottom
    text_widget.see(tk.END)

    # Button frame
    button_frame = ttk.Frame(main_frame)
    button_frame.pack(fill=tk.X, pady=(10, 0))

    # Clear logs button
    def clear_logs():
        log_buffer.clear()
        text_widget.config(state=tk.NORMAL)
        text_widget.delete(1.0, tk.END)
        text_widget.insert(tk.END, "Logs cleared.")
        text_widget.config(state=tk.DISABLED)
        info_label.config(
            text=f"Debug Logs (0 entries) - Logging: {'ON' if config.get('logging_enabled', False) else 'OFF'}"
        )

    # Export logs button
    def export_logs():
        if not log_buffer:
            messagebox.showinfo("Export Logs", "No logs to export.")
            return

        from tkinter import filedialog

        file_path = filedialog.asksaveasfilename(
            title="Export Logs",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )

        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    for entry in log_buffer:
                        f.write(entry + "\n")
                messagebox.showinfo(
                    "Export Complete", f"Logs exported to:\n{file_path}"
                )
            except Exception as e:
                messagebox.showerror(
                    "Export Error", f"Failed to export logs:\n{str(e)}"
                )

    # Refresh logs button
    def refresh_logs():
        text_widget.config(state=tk.NORMAL)
        text_widget.delete(1.0, tk.END)
        if log_buffer:
            for entry in log_buffer:
                text_widget.insert(tk.END, entry + "\n")
        else:
            text_widget.insert(
                tk.END,
                "No log entries available.\nEnable logging to see debug messages here.",
            )
        text_widget.config(state=tk.DISABLED)
        text_widget.see(tk.END)
        info_label.config(
            text=f"Debug Logs ({len(log_buffer)} entries) - Logging: {'ON' if config.get('logging_enabled', False) else 'OFF'}"
        )

    ttk.Button(button_frame, text="Clear Logs", command=clear_logs).pack(
        side=tk.LEFT, padx=(0, 5)
    )
    ttk.Button(button_frame, text="Export Logs", command=export_logs).pack(
        side=tk.LEFT, padx=(0, 5)
    )
    ttk.Button(button_frame, text="Refresh", command=refresh_logs).pack(
        side=tk.LEFT, padx=(0, 5)
    )
    ttk.Button(button_frame, text="Close", command=log_window.destroy).pack(
        side=tk.RIGHT
    )


def get_clipboard_text():
    try:
        result = subprocess.run(
            [
                "powershell.exe",
                "-Command",
                "Get-Clipboard -Raw",
            ],
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
            creationflags=CREATE_NO_WINDOW,
        )
        return result.stdout.strip()
    except FileNotFoundError:
        log("Error: powershell.exe not found. Cannot monitor clipboard.")
        raise
    except subprocess.CalledProcessError as e:
        return ""
    except Exception as e:
        log(f"Unexpected error getting clipboard text: {e}")
        return ""


class MainApplication:
    def __init__(self):
        self.root = tk.Tk()

        # Immediately hide the window before any setup to prevent flash
        # self.root.withdraw()

        self.root.title("G-Downloader")
        self.root.geometry("1000x600")
        self.root.minsize(800, 500)
        center_window(self.root, 1000, 600)

        # Set window icon
        try:
            self.root.iconbitmap("./icon.ico")
        except Exception as e:
            log(f"Could not set window icon: {e}")

        # Center the window on screen (for when it's shown later)
        center_window(self.root, 1000, 600)

        # Configure ttk style for radio buttons
        style = ttk.Style(self.root)
        style.configure("TRadiobutton", font=("Arial", 8))

        # Load history
        self.history = load_history()

        # System tray icon
        self.tray_icon = None
        self.setup_tray()

        # Clipboard monitoring
        self.clipboard_monitor_active = config.get("auto_monitor", True)
        self.monitor_thread = None

        # Thumbnail tooltip
        self.thumbnail_tooltip = None
        self.thumbnail_cache = {}  # Cache for downloaded thumbnails
        self.thumbnail_preload_thread = None
        self.thumbnail_preload_active = False

        # Thumbnail generation status
        self.thumbnails_generating = False

        # Track selected entry for thumbnail hover
        self.selected_entry_id = None

        self.setup_ui()
        self.setup_clipboard_monitor()

        # Bind window close event
        self.root.protocol("WM_DELETE_WINDOW", self.hide_to_tray)

        # Ensure tray icon is visible (window is already hidden)
        if self.tray_icon:
            self.tray_icon.visible = True

    def setup_tray(self):
        """Setup system tray icon"""
        try:
            # Get the icon path from current directory
            icon_path = "./icon.ico"

            icon_image = Image.open(icon_path)

            menu = pystray.Menu(
                pystray.MenuItem("Show", self.show_window),
                pystray.MenuItem("Exit", self.quit_app),
            )

            # Create a wrapper function for double-click that doesn't expect arguments
            def on_double_click():
                self.show_window()

            # Set default action for double-click to show window
            self.tray_icon = pystray.Icon(
                "g-downloader",
                icon_image,
                "G-Downloader",
                menu,
                default=on_double_click,
            )

            # Start tray icon in a separate thread
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
        except Exception as e:
            log(f"Error setting up tray icon: {e}")

    def setup_menu_bar(self):
        """Setup the menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(
            label="New Download...", command=self.new_download, accelerator="Ctrl+N"
        )
        file_menu.add_separator()
        file_menu.add_command(label="Export History...", command=self.export_history)
        file_menu.add_command(label="Export Logs...", command=self.export_logs_menu)
        file_menu.add_separator()
        file_menu.add_command(label="Import Settings...", command=self.import_settings)
        file_menu.add_command(label="Export Settings...", command=self.export_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit_app, accelerator="Ctrl+Q")

        # Edit Menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(
            label="Preferences...", command=self.show_preferences, accelerator="Ctrl+,"
        )
        edit_menu.add_separator()
        edit_menu.add_command(label="Clear History", command=self.clear_history_menu)
        edit_menu.add_command(label="Clear Logs", command=self.clear_logs_menu)

        # Tools Menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(
            label="Refresh History", command=self.refresh_history_view, accelerator="F5"
        )
        tools_menu.add_command(
            label="Generate Thumbnails", command=self.manual_thumbnail_generation
        )
        tools_menu.add_command(label="Clean History", command=self.clean_history)
        tools_menu.add_command(
            label="Import Existing Files", command=self.import_existing_files
        )
        tools_menu.add_separator()
        tools_menu.add_command(
            label="View Logs", command=self.show_logs, accelerator="Ctrl+L"
        )

        # View Menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_checkbutton(
            label="Auto-monitor Clipboard",
            variable=self.monitor_var,
            command=self.toggle_monitor,
        )
        view_menu.add_checkbutton(
            label="Show Thumbnails",
            variable=self.thumbnail_var,
            command=self.toggle_thumbnails,
        )
        view_menu.add_checkbutton(
            label="Enable Notifications",
            variable=self.notifications_var,
            command=self.toggle_notifications,
        )
        view_menu.add_checkbutton(
            label="Debug Logging",
            variable=self.logging_var,
            command=self.toggle_logging,
        )
        view_menu.add_separator()
        view_menu.add_command(label="YouTube", command=lambda: self.notebook.select(0))
        view_menu.add_command(
            label="Instagram", command=lambda: self.notebook.select(1)
        )
        view_menu.add_command(label="TikTok", command=lambda: self.notebook.select(2))

        # Help Menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(
            label="Open Downloads Folder", command=self.open_downloads_folder
        )
        help_menu.add_separator()
        help_menu.add_command(label="Check for Updates", command=self.check_for_updates)
        help_menu.add_command(label="About G-Downloader", command=self.show_about)

        # Bind keyboard shortcuts
        self.root.bind_all("<Control-n>", lambda e: self.new_download())
        self.root.bind_all("<Control-q>", lambda e: self.quit_app())
        self.root.bind_all("<Control-comma>", lambda e: self.show_preferences())
        self.root.bind_all("<F5>", lambda e: self.refresh_history_view())
        self.root.bind_all("<Control-l>", lambda e: self.show_logs())

    def setup_ui(self):
        """Setup the main user interface"""
        # Container frame to center content
        container_frame = ttk.Frame(self.root)
        container_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        # Main frame - centered with reasonable padding
        main_frame = ttk.Frame(container_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=5)

        # Settings frame
        settings_frame = ttk.LabelFrame(main_frame, text="Settings")
        settings_frame.pack(fill=tk.X, pady=(0, 10))

        # Default save path
        path_frame = ttk.Frame(settings_frame)
        path_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(path_frame, text="Default Save Path:").pack(side=tk.LEFT)
        self.path_var = tk.StringVar(value=config["base_dir"])
        path_entry = ttk.Entry(path_frame, textvariable=self.path_var, width=50)
        path_entry.pack(side=tk.LEFT, padx=(10, 5), fill=tk.X, expand=True)

        ttk.Button(path_frame, text="Browse", command=self.browse_path).pack(
            side=tk.RIGHT
        )

        # Initialize variables (needed for menu bar)
        self.monitor_var = tk.BooleanVar(value=self.clipboard_monitor_active)
        self.notifications_var = tk.BooleanVar(
            value=config.get("notifications_enabled", True)
        )
        self.thumbnail_var = tk.BooleanVar(value=config.get("show_thumbnails", True))
        self.logging_var = tk.BooleanVar(value=config.get("logging_enabled", False))

        # Status frame
        status_frame = ttk.Frame(settings_frame)
        status_frame.pack(fill=tk.X, padx=10, pady=5)

        # Status label
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(status_frame, textvariable=self.status_var).pack(side=tk.LEFT)

        # Create menu bar after all variables are initialized
        self.setup_menu_bar()

        # Notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Create tabs for each platform
        self.youtube_tab = self.create_platform_tab("YouTube")
        self.instagram_tab = self.create_platform_tab("Instagram")
        self.tiktok_tab = self.create_platform_tab("TikTok")

        self.notebook.add(self.youtube_tab, text="YouTube")
        self.notebook.add(self.instagram_tab, text="Instagram")
        self.notebook.add(self.tiktok_tab, text="TikTok")

        # Automatically clean deleted files and import existing files on startup
        self.auto_clean_history()
        self.auto_import_existing_files()
        self.populate_history()

        # Start thumbnail preloading in background
        self.start_thumbnail_preload()

        # URL input frame
        url_frame = ttk.LabelFrame(main_frame, text="Download URL")
        url_frame.pack(fill=tk.X, pady=(10, 0))

        url_input_frame = ttk.Frame(url_frame)
        url_input_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(url_input_frame, text="URL:").pack(side=tk.LEFT)
        self.url_var = tk.StringVar()
        url_entry = ttk.Entry(url_input_frame, textvariable=self.url_var, width=60)
        url_entry.pack(side=tk.LEFT, padx=(10, 5), fill=tk.X, expand=True)

        ttk.Button(url_input_frame, text="Download", command=self.download_url).pack(
            side=tk.RIGHT
        )

        # Bind Enter key to download
        url_entry.bind("<Return>", lambda e: self.download_url())

    def create_platform_tab(self, platform):
        """Create a tab for a specific platform"""
        tab = ttk.Frame(self.notebook)

        # Create treeview for downloads
        columns = ("Title", "Format", "Date")
        tree = ttk.Treeview(tab, columns=columns, show="headings")

        # Configure columns
        tree.heading("Title", text="Title")
        tree.heading("Format", text="Format")
        tree.heading("Date", text="Date Downloaded")

        tree.column("Title", width=400, anchor="w")
        tree.column("Format", width=80, anchor="center")
        tree.column("Date", width=150, anchor="center")

        # Bind double-click event
        tree.bind("<Double-1>", self.on_history_item_double_click)

        # Bind click event to select entry for thumbnail preview
        tree.bind("<Button-1>", self.on_treeview_click)

        # Bind hover events for thumbnail preview (only on selected entry)
        tree.bind("<Motion>", self.on_treeview_motion)
        tree.bind("<Leave>", self.on_treeview_leave)

        # Scrollbar
        scrollbar = ttk.Scrollbar(tab, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        # Pack widgets
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Store reference
        setattr(self, f"{platform.lower()}_tree", tree)

        return tab

    def browse_path(self):
        """Browse for default save path"""
        path = filedialog.askdirectory(initialdir=self.path_var.get())
        if path:
            self.path_var.set(path)
            # Update config
            config["base_dir"] = path
            config["yt_mp3_dir"] = str(Path(path) / "YouTube" / "MP3")
            config["yt_mp4_dir"] = str(Path(path) / "YouTube" / "MP4")
            config["insta_dir"] = str(Path(path) / "Instagram")
            config["tiktok_dir"] = str(Path(path) / "TikTok")
            save_config(config)
            create_directories()

    def refresh_history_view(self):
        """Reloads history, cleans deleted files, imports existing files, and updates the display."""
        try:
            # Start with loading current history
            original_count = len(load_history())
            self.history = load_history()

            # Clean up deleted files first
            self.status_var.set("Cleaning deleted files...")
            self.root.update_idletasks()  # Update UI immediately
            cleaned_before = len(self.history)
            self.auto_clean_history()
            cleaned_after = len(self.history)
            removed_count = cleaned_before - cleaned_after

            # Then import existing files
            self.status_var.set("Importing existing files...")
            self.root.update_idletasks()  # Update UI immediately
            import_before = len(self.history)
            self.auto_import_existing_files()
            import_after = len(self.history)
            imported_count = import_after - import_before

            # Update display
            self.populate_history()

            # Restart thumbnail preload if new files were imported
            if imported_count > 0:
                self.stop_thumbnail_preload()
                # Clear cache for preloaded thumbnails to regenerate for new files
                keys_to_remove = [
                    k for k in self.thumbnail_cache.keys() if k.endswith(":low")
                ]
                for key in keys_to_remove:
                    del self.thumbnail_cache[key]
                self.start_thumbnail_preload()

            # Show comprehensive status
            status_parts = []
            if removed_count > 0:
                status_parts.append(f"Removed {removed_count} deleted files")
            if imported_count > 0:
                status_parts.append(f"Imported {imported_count} existing files")

            if status_parts:
                self.status_var.set(f"History refreshed: {', '.join(status_parts)}")
            else:
                self.status_var.set("History refreshed - no changes needed")

        except Exception as e:
            log(f"Error refreshing history: {e}")
            self.status_var.set("Error refreshing history")
            messagebox.showerror("Refresh Error", f"Error refreshing history: {str(e)}")

    def auto_clean_history(self):
        """Automatically remove entries from history where files no longer exist (silent)."""
        try:
            cleaned_history = []
            removed_count = 0

            for entry in self.history:
                file_path = entry.get("file_path", "")
                if file_path and Path(file_path).exists():
                    # File still exists, keep the entry
                    cleaned_history.append(entry)
                else:
                    # File doesn't exist, remove from history
                    removed_count += 1
                    try:
                        title = entry.get("title", "Unknown")
                        log(f"Auto-removed deleted file from history: {title}")
                    except UnicodeEncodeError:
                        log(
                            "Auto-removed deleted file from history: [File with special characters]"
                        )

            # Save the cleaned history if changes were made
            if removed_count > 0:
                save_history(cleaned_history)
                self.history = cleaned_history
                log(f"Auto-cleaned {removed_count} deleted files from history")

        except Exception as e:
            log(f"Error auto-cleaning history: {e}")

    def auto_import_existing_files(self):
        """Automatically import existing files from download directories into history (silent)."""
        try:
            imported_count = 0
            existing_history = load_history()
            existing_paths = {entry.get("file_path") for entry in existing_history}

            # Define directories and their corresponding platforms/formats
            scan_dirs = [
                (config["yt_mp3_dir"], "YouTube", "MP3"),
                (config["yt_mp4_dir"], "YouTube", "MP4"),
                (config["insta_dir"], "Instagram", "MP4"),
                (config["tiktok_dir"], "TikTok", "MP4"),
            ]

            for dir_path, platform, format_type in scan_dirs:
                directory = Path(dir_path)
                if not directory.exists():
                    continue

                # Scan for media files - expanded pattern list for more formats
                patterns = [
                    "*.mp4",
                    "*.mp3",
                    "*.webm",
                    "*.m4a",
                    "*.jpg",
                    "*.png",
                    "*.mkv",
                    "*.avi",
                    "*.mov",
                    "*.flv",
                    "*.m4v",
                    "*.aac",
                    "*.wav",
                    "*.flac",
                    "*.ogg",
                    "*.gif",
                    "*.webp",
                ]
                for pattern in patterns:
                    for file_path in directory.glob(pattern):
                        file_path_str = str(file_path)

                        # Skip if already in history
                        if file_path_str in existing_paths:
                            continue

                        try:
                            # Extract title from filename (remove extension and clean up)
                            title = file_path.stem
                            # Handle Unicode characters properly
                            title = title.replace("_", " ").replace("-", " ")

                            # Clean up any problematic characters that might cause encoding issues
                            title = title.encode("utf-8", errors="ignore").decode(
                                "utf-8"
                            )

                            # Fallback if title is empty after cleaning
                            if not title.strip():
                                title = f"File_{imported_count + 1}"

                            # Determine actual format from file extension
                            actual_format = get_file_format_from_extension(
                                file_path_str
                            )

                            # No need to store thumbnail URLs since we generate them from video files
                            thumbnail_url = ""

                            # Create history entry with creation time
                            entry = {
                                "platform": platform,
                                "title": title,
                                "url": "Imported from existing files",
                                "format": actual_format,
                                "file_path": file_path_str,
                                "timestamp": file_path.stat().st_ctime,  # Use file creation time
                                "thumbnail_url": thumbnail_url,
                            }

                            add_to_history(entry)
                            imported_count += 1

                            # Use safe printing to avoid encoding errors
                            try:
                                log(
                                    f"Auto-imported: {title} ({platform} - {actual_format})"
                                )
                            except UnicodeEncodeError:
                                log(
                                    f"Auto-imported: [File with special characters] ({platform} - {actual_format})"
                                )

                        except Exception as file_error:
                            # Skip files that cause encoding or other errors
                            try:
                                log(
                                    f"Skipped file due to error: {file_path.name} - {str(file_error)}"
                                )
                            except UnicodeEncodeError:
                                log("Skipped file with special characters due to error")
                            continue

            # Update the history in memory
            if imported_count > 0:
                self.history = load_history()
                log(f"Auto-imported {imported_count} existing files to history")

        except Exception as e:
            log(f"Error auto-importing existing files: {e}")

    def start_thumbnail_preload(self):
        """Start background thumbnail preloading for the first 50 entries"""
        if not config.get("show_thumbnails", True):
            return

        if self.thumbnail_preload_active:
            return

        self.thumbnail_preload_active = True
        self.thumbnail_preload_thread = threading.Thread(
            target=self.preload_thumbnails, daemon=True
        )
        self.thumbnail_preload_thread.start()

    def preload_thumbnails(self):
        """Preload thumbnails for the first 50 video entries in low quality"""
        try:
            self.thumbnails_generating = True
            self.root.after(0, lambda: self.status_var.set("Generating thumbnails..."))

            video_entries = []
            for i, entry in enumerate(self.history[:50]):  # First 50 entries only
                file_path = entry.get("file_path", "")
                if file_path and Path(file_path).exists():
                    # Check if it's a video file
                    path_obj = Path(file_path)
                    if path_obj.suffix.lower() in [
                        ".mp4",
                        ".webm",
                        ".avi",
                        ".mkv",
                        ".mov",
                        ".flv",
                        ".m4v",
                        ".3gp",
                    ]:
                        video_entries.append((i, entry, file_path))

            log(f"Debug: Starting preload for {len(video_entries)} video files")

            for count, (index, entry, file_path) in enumerate(video_entries):
                if not self.thumbnail_preload_active:
                    break

                cache_key = f"video:{file_path}:low"

                # Skip if already cached
                if cache_key in self.thumbnail_cache:
                    continue

                # Update status periodically
                if count % 5 == 0:
                    progress_text = (
                        f"Generating thumbnails... ({count + 1}/{len(video_entries)})"
                    )
                    self.root.after(0, lambda t=progress_text: self.status_var.set(t))

                # Generate ultra-low quality thumbnail for speed
                thumbnail_image = generate_video_thumbnail(
                    file_path, max_size=(100, 75), quality="low"
                )

                if thumbnail_image:
                    self.thumbnail_cache[cache_key] = thumbnail_image
                    log(
                        f"Debug: Preloaded thumbnail {count + 1}/{len(video_entries)}: {Path(file_path).name}"
                    )

                # Small delay to prevent overwhelming the system
                time.sleep(0.1)

            self.thumbnails_generating = False
            total_preloaded = len(
                [k for k in self.thumbnail_cache.keys() if k.endswith(":low")]
            )
            self.root.after(
                0,
                lambda: self.status_var.set(
                    f"Thumbnails ready ({total_preloaded} preloaded)"
                ),
            )
            log(
                f"Debug: Thumbnail preload complete - {total_preloaded} thumbnails generated"
            )

        except Exception as e:
            log(f"Error during thumbnail preload: {e}")
            self.thumbnails_generating = False
            self.root.after(0, lambda: self.status_var.set("Thumbnail preload failed"))

    def stop_thumbnail_preload(self):
        """Stop the thumbnail preloading process"""
        self.thumbnail_preload_active = False
        if self.thumbnail_preload_thread and self.thumbnail_preload_thread.is_alive():
            log("Debug: Stopping thumbnail preload...")

    def manual_thumbnail_generation(self):
        """Manually trigger thumbnail generation"""
        if self.thumbnails_generating:
            self.status_var.set("Thumbnails are already being generated...")
            return

        # Stop current preload and restart
        self.stop_thumbnail_preload()

        # Clear existing preloaded thumbnails to force regeneration
        keys_to_remove = [k for k in self.thumbnail_cache.keys() if k.endswith(":low")]
        for key in keys_to_remove:
            del self.thumbnail_cache[key]

        # Start fresh preload
        self.start_thumbnail_preload()

    def clean_history(self):
        """Manually remove entries from history where the files no longer exist."""
        try:
            original_history = load_history()
            cleaned_history = []
            removed_count = 0

            for entry in original_history:
                file_path = entry.get("file_path", "")
                if file_path and Path(file_path).exists():
                    # File still exists, keep the entry
                    cleaned_history.append(entry)
                else:
                    # File doesn't exist, remove from history
                    removed_count += 1
                    try:
                        title = entry.get("title", "Unknown")
                        log(f"Removing deleted file from history: {title}")
                    except UnicodeEncodeError:
                        log(
                            "Removing deleted file from history: [File with special characters]"
                        )

            # Save the cleaned history
            if removed_count > 0:
                save_history(cleaned_history)
                self.history = cleaned_history
                self.populate_history()

                self.status_var.set(
                    f"Removed {removed_count} deleted files from history"
                )
                messagebox.showinfo(
                    "History Cleaned",
                    f"Removed {removed_count} entries for files that no longer exist.",
                )
            else:
                self.status_var.set("No deleted files found in history")
                messagebox.showinfo(
                    "History Clean",
                    "All files in history still exist. No cleanup needed.",
                )

        except Exception as e:
            log(f"Error cleaning history: {e}")
            messagebox.showerror("Clean Error", f"Error cleaning history: {str(e)}")
            self.status_var.set("History clean failed")

    def import_existing_files(self):
        """Import existing files from download directories into history."""
        try:
            imported_count = 0
            existing_history = load_history()
            existing_paths = {entry.get("file_path") for entry in existing_history}

            # Define directories and their corresponding platforms/formats
            scan_dirs = [
                (config["yt_mp3_dir"], "YouTube", "MP3"),
                (config["yt_mp4_dir"], "YouTube", "MP4"),
                (config["insta_dir"], "Instagram", "MP4"),
                (config["tiktok_dir"], "TikTok", "MP4"),
            ]

            for dir_path, platform, format_type in scan_dirs:
                directory = Path(dir_path)
                if not directory.exists():
                    continue

                # Scan for media files - expanded pattern list for more formats
                patterns = [
                    "*.mp4",
                    "*.mp3",
                    "*.webm",
                    "*.m4a",
                    "*.jpg",
                    "*.png",
                    "*.mkv",
                    "*.avi",
                    "*.mov",
                    "*.flv",
                    "*.m4v",
                    "*.aac",
                    "*.wav",
                    "*.flac",
                    "*.ogg",
                    "*.gif",
                    "*.webp",
                ]
                for pattern in patterns:
                    for file_path in directory.glob(pattern):
                        file_path_str = str(file_path)

                        # Skip if already in history
                        if file_path_str in existing_paths:
                            continue

                        try:
                            # Extract title from filename (remove extension and clean up)
                            title = file_path.stem
                            # Handle Unicode characters properly
                            title = title.replace("_", " ").replace("-", " ")

                            # Clean up any problematic characters that might cause encoding issues
                            title = title.encode("utf-8", errors="ignore").decode(
                                "utf-8"
                            )

                            # Fallback if title is empty after cleaning
                            if not title.strip():
                                title = f"File_{imported_count + 1}"

                            # Determine actual format from file extension
                            actual_format = get_file_format_from_extension(
                                file_path_str
                            )

                            # No need to store thumbnail URLs since we generate them from video files
                            thumbnail_url = ""

                            # Create history entry with creation time
                            entry = {
                                "platform": platform,
                                "title": title,
                                "url": "Imported from existing files",
                                "format": actual_format,
                                "file_path": file_path_str,
                                "timestamp": file_path.stat().st_ctime,  # Use file creation time
                                "thumbnail_url": thumbnail_url,
                            }

                            add_to_history(entry)
                            imported_count += 1

                            # Use safe printing to avoid encoding errors
                            try:
                                log(f"Imported: {title} ({platform} - {actual_format})")
                            except UnicodeEncodeError:
                                log(
                                    f"Imported: [File with special characters] ({platform} - {actual_format})"
                                )

                        except Exception as file_error:
                            # Skip files that cause encoding or other errors
                            log(
                                f"Skipped file due to error: {file_path.name} - {str(file_error)}"
                            )
                            continue

            # Refresh the display
            self.history = load_history()
            self.populate_history()

            if imported_count > 0:
                self.status_var.set(f"Imported {imported_count} existing files")
                messagebox.showinfo(
                    "Import Complete",
                    f"Successfully imported {imported_count} existing files into history!",
                )
            else:
                self.status_var.set("No new files to import")
                messagebox.showinfo(
                    "Import Complete",
                    "No new files found to import. All existing files are already in history.",
                )

        except Exception as e:
            log(f"Error importing existing files: {e}")
            messagebox.showerror("Import Error", f"Error importing files: {str(e)}")
            self.status_var.set("Import failed")

    def populate_history(self):
        """Populate the treeviews with download history."""
        from datetime import datetime

        # Clear existing items
        self.youtube_tree.delete(*self.youtube_tree.get_children())
        self.instagram_tree.delete(*self.instagram_tree.get_children())
        self.tiktok_tree.delete(*self.tiktok_tree.get_children())

        try:
            log(f"Loading history: {len(self.history)} entries found")
        except UnicodeEncodeError:
            log(f"Loading history: {len(self.history)} entries found")

        for i, entry in enumerate(self.history):
            tree = None
            platform = entry.get("platform")
            try:
                log(
                    f"Processing entry {i}: {platform} - {entry.get('title', 'No title')}"
                )
            except UnicodeEncodeError:
                log(
                    f"Processing entry {i}: {platform} - [Title with special characters]"
                )

            if platform == "YouTube":
                tree = self.youtube_tree
            elif platform == "Instagram":
                tree = self.instagram_tree
            elif platform == "TikTok":
                tree = self.tiktok_tree

            if tree:
                try:
                    dt_object = datetime.fromtimestamp(
                        entry.get("timestamp", time.time())
                    )
                    date_str = dt_object.strftime("%Y-%m-%d %H:%M:%S")

                    # Create a unique ID using only the index to avoid Unicode issues
                    unique_id = f"item_{i}"

                    tree.insert(
                        "",
                        "end",
                        values=(
                            entry.get("title", "Unknown Title"),
                            entry.get("format", "Unknown"),
                            date_str,
                        ),
                        iid=unique_id,
                    )
                    safe_log(
                        f"Added to {platform} tree: {entry.get('title', 'Unknown Title')}"
                    )
                except Exception as e:
                    log(f"Error adding entry to tree: {e}")

    def on_treeview_click(self, event):
        """Handle single click on treeview to select entry for thumbnail preview"""
        tree = event.widget
        item = tree.identify_row(event.y)

        if item:
            self.selected_entry_id = item
            log(f"Debug: Selected entry for thumbnail preview: {item}")
        else:
            self.selected_entry_id = None
            # Hide tooltip when clicking on empty space
            self.hide_thumbnail_tooltip()

    def on_history_item_double_click(self, event):
        """Handle double-click on a history item to open the file."""
        tree = event.widget
        selection = tree.selection()
        if not selection:
            return

        # Extract index from the unique ID (format: "item_index")
        unique_id = selection[0]
        try:
            index = int(unique_id.split("_")[1])
            if 0 <= index < len(self.history):
                entry = self.history[index]
                file_path_str = entry.get("file_path", "")
                if not file_path_str:
                    messagebox.showwarning(
                        "Error", "No file path associated with this entry."
                    )
                    return
                file_path = Path(file_path_str)
            else:
                messagebox.showwarning("Error", "Invalid history entry.")
                return
        except (ValueError, IndexError):
            messagebox.showwarning("Error", "Could not determine file path.")
            return

        try:
            if file_path.exists():
                if sys.platform == "win32":
                    os.startfile(file_path)
                elif sys.platform == "darwin":  # macOS
                    subprocess.run(["open", file_path])
                else:  # linux
                    subprocess.run(["xdg-open", file_path])
            else:
                messagebox.showwarning(
                    "File Not Found",
                    f"The file could not be found at:\n{file_path}\n\nIt may have been moved or deleted.",
                )
        except Exception as e:
            messagebox.showerror("Error", f"Could not open the file:\n{e}")

    def on_treeview_motion(self, event):
        """Handle mouse motion over treeview for thumbnail preview (only on selected entry)"""
        if not config.get("show_thumbnails", True):
            return

        tree = event.widget
        item = tree.identify_row(event.y)

        # Only show thumbnail if hovering over the selected entry
        if item and item == self.selected_entry_id:
            # Get the history entry for this item
            unique_id = item
            try:
                index = int(unique_id.split("_")[1])
                if 0 <= index < len(self.history):
                    entry = self.history[index]
                    thumbnail_url = entry.get("thumbnail_url", "")

                    # Safe debug printing to avoid encoding errors
                    try:
                        log(
                            f"Debug: Hovering over item {index}, thumbnail_url: {thumbnail_url}"
                        )
                    except UnicodeEncodeError:
                        log(
                            f"Debug: Hovering over item {index}, thumbnail_url: [URL with special characters]"
                        )

                    # Always try to generate thumbnail from local video file first
                    file_path = entry.get("file_path", "")
                    if file_path and Path(file_path).exists():
                        try:
                            log(
                                f"Debug: Generating thumbnail from local file: {file_path}"
                            )
                        except UnicodeEncodeError:
                            log(
                                "Debug: Generating thumbnail from local file: [File with special characters]"
                            )
                        self.show_video_thumbnail_tooltip(
                            event, file_path, entry.get("title", "Unknown")
                        )
                    elif thumbnail_url and thumbnail_url.strip():
                        try:
                            log(
                                f"Debug: Using stored thumbnail URL as fallback: {thumbnail_url}"
                            )
                        except UnicodeEncodeError:
                            log(
                                "Debug: Using stored thumbnail URL as fallback: [URL with special characters]"
                            )
                        self.show_thumbnail_tooltip(
                            event, thumbnail_url, entry.get("title", "Unknown")
                        )
                    else:
                        # Try to get thumbnail URL if it doesn't exist
                        url = entry.get("url", "")
                        if url and url != "Imported from existing files":
                            platform = entry.get("platform", "")
                            try:
                                log(
                                    f"Debug: Fetching thumbnail for URL as last resort: {url}"
                                )
                            except UnicodeEncodeError:
                                log(
                                    "Debug: Fetching thumbnail for URL as last resort: [URL with special characters]"
                                )
                            self.fetch_and_show_thumbnail(
                                event, url, platform, entry.get("title", "Unknown")
                            )
                        else:
                            log("Debug: No thumbnail available for this item")
                            # No thumbnail available, hide tooltip
                            self.hide_thumbnail_tooltip()
                else:
                    self.hide_thumbnail_tooltip()
            except (ValueError, IndexError) as e:
                try:
                    log(f"Debug: Error parsing item ID: {e}")
                except UnicodeEncodeError:
                    log("Debug: Error parsing item ID: [Error with special characters]")
                self.hide_thumbnail_tooltip()
            except UnicodeEncodeError as e:
                try:
                    log(f"Debug: Unicode encoding error in treeview motion: {e}")
                except:
                    log(
                        "Debug: Unicode encoding error in treeview motion: [Error with special characters]"
                    )
                self.hide_thumbnail_tooltip()
        else:
            # Not hovering over the selected entry, hide tooltip
            self.hide_thumbnail_tooltip()

    def on_treeview_leave(self, event):
        """Handle mouse leaving treeview"""
        self.hide_thumbnail_tooltip()

    def fetch_and_show_thumbnail(self, event, url, platform, title):
        """Fetch thumbnail URL and show tooltip"""
        # Store event position for later use
        event_x, event_y = event.x_root, event.y_root

        def fetch_in_thread():
            try:
                log(f"Debug: Fetching thumbnail for URL: {url}")
                info = get_video_info(url, platform)
                if info and info.get("thumbnail"):
                    thumbnail_url = info["thumbnail"]
                    log(f"Debug: Found thumbnail URL: {thumbnail_url}")

                    # Create a mock event object with stored position
                    class MockEvent:
                        def __init__(self, x_root, y_root):
                            self.x_root = x_root
                            self.y_root = y_root

                    mock_event = MockEvent(event_x, event_y)

                    # Update the UI in the main thread
                    self.root.after(
                        0,
                        lambda: self.show_thumbnail_tooltip(
                            mock_event, thumbnail_url, title
                        ),
                    )
                else:
                    log(f"Debug: No thumbnail found for URL: {url}")
            except Exception as e:
                log(f"Debug: Error fetching thumbnail: {e}")

        # Run in background thread to avoid blocking UI
        threading.Thread(target=fetch_in_thread, daemon=True).start()

    def show_video_thumbnail_tooltip(self, event, video_path, title):
        """Show thumbnail tooltip generated from local video file"""
        # Store event position for later use
        event_x, event_y = event.x_root, event.y_root

        # Check for preloaded low quality thumbnail first
        low_quality_key = f"video:{video_path}:low"
        high_quality_key = f"video:{video_path}:high"

        if low_quality_key in self.thumbnail_cache:
            # Show preloaded low quality thumbnail immediately
            log("Debug: Using preloaded low quality thumbnail")

            class MockEvent:
                def __init__(self, x_root, y_root):
                    self.x_root = x_root
                    self.y_root = y_root

            mock_event = MockEvent(event_x, event_y)
            self.show_generated_thumbnail_tooltip(
                mock_event, self.thumbnail_cache[low_quality_key], title, quality="low"
            )

            # Start generating high quality version in background if not cached
            if high_quality_key not in self.thumbnail_cache:

                def generate_high_quality():
                    try:
                        thumbnail_image = generate_video_thumbnail(
                            video_path, max_size=(250, 200), quality="high"
                        )
                        if thumbnail_image:
                            self.thumbnail_cache[high_quality_key] = thumbnail_image
                            log("Debug: High quality thumbnail generated and cached")
                    except Exception as e:
                        log(f"Debug: Error generating high quality thumbnail: {e}")

                threading.Thread(target=generate_high_quality, daemon=True).start()

        elif high_quality_key in self.thumbnail_cache:
            # Use cached high quality thumbnail
            log("Debug: Using cached high quality thumbnail")

            class MockEvent:
                def __init__(self, x_root, y_root):
                    self.x_root = x_root
                    self.y_root = y_root

            mock_event = MockEvent(event_x, event_y)
            self.show_generated_thumbnail_tooltip(
                mock_event,
                self.thumbnail_cache[high_quality_key],
                title,
                quality="high",
            )

        else:
            # No cached thumbnail, generate on demand
            def generate_in_thread():
                try:
                    log(
                        f"Debug: Generating on-demand thumbnail from video: {video_path}"
                    )

                    # Generate high quality thumbnail
                    thumbnail_image = generate_video_thumbnail(
                        video_path, max_size=(250, 200), quality="high"
                    )
                    if thumbnail_image:
                        self.thumbnail_cache[high_quality_key] = thumbnail_image
                        log("Debug: On-demand video thumbnail generated successfully")

                        # Create a mock event object with stored position
                        class MockEvent:
                            def __init__(self, x_root, y_root):
                                self.x_root = x_root
                                self.y_root = y_root

                        mock_event = MockEvent(event_x, event_y)

                        # Update the UI in the main thread
                        self.root.after(
                            0,
                            lambda: self.show_generated_thumbnail_tooltip(
                                mock_event, thumbnail_image, title, quality="high"
                            ),
                        )
                    else:
                        log("Debug: Failed to generate on-demand video thumbnail")

                except Exception as e:
                    log(f"Debug: Error generating on-demand video thumbnail: {e}")

            # Run in background thread to avoid blocking UI
            threading.Thread(target=generate_in_thread, daemon=True).start()

    def show_generated_thumbnail_tooltip(
        self, event, thumbnail_image, title, quality="high"
    ):
        """Show tooltip with pre-generated thumbnail image"""
        try:
            log(f"Debug: Displaying {quality} quality thumbnail tooltip for: {title}")

            # Hide existing tooltip
            self.hide_thumbnail_tooltip()

            if not thumbnail_image:
                log("Debug: No thumbnail image provided")  # Debug
                return

            # Create tooltip window
            self.thumbnail_tooltip = tk.Toplevel(self.root)
            self.thumbnail_tooltip.wm_overrideredirect(True)
            self.thumbnail_tooltip.configure(bg="white")

            # Position tooltip near mouse
            x = event.x_root + 15
            y = event.y_root - 120

            # Adjust position to keep tooltip on screen
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()

            tooltip_width = 270  # thumbnail width + padding
            tooltip_height = 280  # thumbnail height + text + padding (increased for quality indicator)

            if x + tooltip_width > screen_width:
                x = event.x_root - tooltip_width - 15
            if y + tooltip_height > screen_height:
                y = event.y_root - tooltip_height - 10
            if y < 0:
                y = event.y_root + 30

            self.thumbnail_tooltip.wm_geometry(f"+{x}+{y}")

            # Create borderless frame
            frame = tk.Frame(
                self.thumbnail_tooltip,
                bg="white",
                relief="flat",
                bd=0,
            )
            frame.pack(fill="both", expand=True, padx=0, pady=0)

            # Add thumbnail
            thumbnail_label = tk.Label(frame, image=thumbnail_image, bg="white", bd=0)
            thumbnail_label.image = thumbnail_image  # Keep reference
            thumbnail_label.pack(pady=(8, 5))

            # Add title (truncated if too long)
            title_text = title if len(title) <= 35 else title[:32] + "..."
            title_label = tk.Label(
                frame,
                text=title_text,
                bg="white",
                font=("Arial", 9, "bold"),
                wraplength=240,
                justify="center",
            )
            title_label.pack(pady=(0, 5))

            # Add quality and source indicator
            if quality == "low":
                quality_icon = "⚡"
                quality_text = "Fast preview"
                quality_color = "orange"
            else:
                quality_icon = "🎯"
                quality_text = "High quality"
                quality_color = "green"

            source_label = tk.Label(
                frame,
                text=f"📹 Generated from video • {quality_icon} {quality_text}",
                bg="white",
                font=("Arial", 7),
                fg=quality_color,
            )
            source_label.pack(pady=(0, 6))

            safe_log(f"Debug: {quality} quality thumbnail tooltip created for: {title}")

        except Exception as e:
            log(f"Error showing generated thumbnail tooltip: {e}")
            self.hide_thumbnail_tooltip()

    def show_thumbnail_tooltip(self, event, thumbnail_url, title):
        """Show thumbnail tooltip at mouse position"""
        try:
            log(
                f"Debug: Attempting to show thumbnail for URL: {thumbnail_url}"
            )  # Debug

            # Hide existing tooltip
            self.hide_thumbnail_tooltip()

            # Check cache first
            if thumbnail_url in self.thumbnail_cache:
                thumbnail_image = self.thumbnail_cache[thumbnail_url]
                log("Debug: Using cached thumbnail")  # Debug
            else:
                log("Debug: Downloading thumbnail...")  # Debug
                # Download thumbnail
                thumbnail_image = download_thumbnail(thumbnail_url, max_size=(250, 200))
                if thumbnail_image:
                    self.thumbnail_cache[thumbnail_url] = thumbnail_image
                    log("Debug: Thumbnail downloaded successfully")  # Debug
                else:
                    log("Debug: Failed to download thumbnail")  # Debug
                    return  # No thumbnail available

            if not thumbnail_image:
                log("Debug: No thumbnail image available")  # Debug
                return

            # Create tooltip window
            self.thumbnail_tooltip = tk.Toplevel(self.root)
            self.thumbnail_tooltip.wm_overrideredirect(True)
            self.thumbnail_tooltip.configure(bg="white")

            # Position tooltip near mouse
            x = event.x_root + 15
            y = event.y_root - 120

            # Adjust position to keep tooltip on screen
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()

            tooltip_width = 270  # thumbnail width + padding
            tooltip_height = 260  # thumbnail height + text + padding

            if x + tooltip_width > screen_width:
                x = event.x_root - tooltip_width - 15
            if y + tooltip_height > screen_height:
                y = event.y_root - tooltip_height - 10
            if y < 0:
                y = event.y_root + 30

            self.thumbnail_tooltip.wm_geometry(f"+{x}+{y}")

            # Create borderless frame
            frame = tk.Frame(
                self.thumbnail_tooltip,
                bg="white",
                relief="flat",
                bd=0,
            )
            frame.pack(fill="both", expand=True, padx=0, pady=0)

            # Add thumbnail
            thumbnail_label = tk.Label(frame, image=thumbnail_image, bg="white", bd=0)
            thumbnail_label.image = thumbnail_image  # Keep reference
            thumbnail_label.pack(pady=(8, 5))

            # Add title (truncated if too long)
            title_text = title if len(title) <= 35 else title[:32] + "..."
            title_label = tk.Label(
                frame,
                text=title_text,
                bg="white",
                font=("Arial", 9, "bold"),
                wraplength=240,
                justify="center",
            )
            title_label.pack(pady=(0, 8))

            safe_log(f"Debug: Thumbnail tooltip created for: {title}")

        except Exception as e:
            log(f"Error showing thumbnail tooltip: {e}")
            self.hide_thumbnail_tooltip()

    def hide_thumbnail_tooltip(self):
        """Hide the thumbnail tooltip"""
        if self.thumbnail_tooltip:
            try:
                self.thumbnail_tooltip.destroy()
            except:
                pass
            self.thumbnail_tooltip = None

    def toggle_monitor(self):
        """Toggle clipboard monitoring"""
        self.clipboard_monitor_active = self.monitor_var.get()
        config["auto_monitor"] = self.clipboard_monitor_active
        save_config(config)

        if self.clipboard_monitor_active:
            self.setup_clipboard_monitor()
            self.status_var.set("Monitoring clipboard...")
        else:
            self.status_var.set("Clipboard monitoring disabled")

    def toggle_notifications(self):
        """Toggle notifications"""
        notifications_enabled = self.notifications_var.get()
        config["notifications_enabled"] = notifications_enabled
        save_config(config)

        if notifications_enabled:
            self.status_var.set("Notifications enabled")
        else:
            self.status_var.set("Notifications disabled")

    def toggle_thumbnails(self):
        """Toggle thumbnail previews on hover"""
        thumbnails_enabled = self.thumbnail_var.get()
        config["show_thumbnails"] = thumbnails_enabled
        save_config(config)

        if thumbnails_enabled:
            self.status_var.set("Thumbnail previews enabled")
            # Start thumbnail preloading
            self.start_thumbnail_preload()
        else:
            self.status_var.set("Thumbnail previews disabled")
            # Stop thumbnail preloading and hide any current tooltip
            self.stop_thumbnail_preload()
            self.hide_thumbnail_tooltip()

    def toggle_logging(self):
        """Toggle debug logging"""
        logging_enabled = self.logging_var.get()
        config["logging_enabled"] = logging_enabled
        save_config(config)

        if logging_enabled:
            self.status_var.set("Debug logging enabled")
            log("Debug logging has been enabled")
        else:
            self.status_var.set("Debug logging disabled")
            log("Debug logging has been disabled")

    def show_logs(self):
        """Show the log viewer window"""
        show_log_viewer()

    def setup_clipboard_monitor(self):
        """Setup clipboard monitoring"""
        if self.clipboard_monitor_active and not self.monitor_thread:
            self.monitor_thread = threading.Thread(
                target=self.clipboard_monitor, daemon=True
            )
            self.monitor_thread.start()

    def clipboard_monitor(self):
        """Monitor clipboard for URLs"""
        last_text = ""
        processed_urls = set()

        while self.clipboard_monitor_active:
            try:
                current_text = get_clipboard_text()

                if (
                    current_text
                    and current_text != last_text
                    and current_text not in processed_urls
                ):

                    platform = None
                    if is_youtube_url(current_text):
                        platform = "YouTube"
                    elif is_instagram_url(current_text):
                        platform = "Instagram"
                    elif is_tiktok_url(current_text):
                        platform = "TikTok"

                    if platform:
                        self.root.after(
                            0, lambda: self.handle_detected_url(current_text, platform)
                        )
                        processed_urls.add(current_text)

                last_text = current_text
                time.sleep(1)

            except Exception as e:
                log(f"Error in clipboard monitoring: {e}")
                time.sleep(5)

    def handle_detected_url(self, url, platform):
        """Handle detected URL from clipboard"""
        self.url_var.set(url)
        # Switch to appropriate tab
        if platform == "YouTube":
            self.notebook.select(0)
        elif platform == "Instagram":
            self.notebook.select(1)
        elif platform == "TikTok":
            self.notebook.select(2)

        # Show notification and automatically open download banner
        self.show_notification(f"Detected {platform} URL", url)

        # Automatically show download banner after a short delay
        self.root.after(1000, lambda: self.show_download_banner(url, platform))

    def download_url(self):
        """Download the URL from the input field"""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Please enter a URL")
            return

        platform = None
        if is_youtube_url(url):
            platform = "YouTube"
        elif is_instagram_url(url):
            platform = "Instagram"
        elif is_tiktok_url(url):
            platform = "TikTok"

        if not platform:
            messagebox.showerror("Error", "Unsupported URL format")
            return

        # Get video info and show download dialog
        self.show_download_dialog(url, platform)

    def show_download_dialog(self, url, platform):
        """Show download options dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Download {platform} Content")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()

        # Get video info
        info = get_video_info(url, platform)

        # Video info frame
        info_frame = ttk.LabelFrame(dialog, text="Video Information")
        info_frame.pack(fill=tk.X, padx=10, pady=5)

        if info:
            # Try to show thumbnail (prefer generating from video if available)
            thumbnail = None
            if info.get("thumbnail"):
                thumbnail = download_thumbnail(info["thumbnail"])

            if thumbnail:
                thumbnail_label = ttk.Label(info_frame, image=thumbnail)
                thumbnail_label.image = thumbnail  # Keep reference
                thumbnail_label.pack(pady=5)

            # Title
            title_label = ttk.Label(
                info_frame, text=f"Title: {info['title']}", wraplength=450
            )
            title_label.pack(pady=2)

            # Uploader
            if info.get("uploader"):
                uploader_label = ttk.Label(
                    info_frame, text=f"Uploader: {info['uploader']}"
                )
                uploader_label.pack(pady=2)
        else:
            ttk.Label(info_frame, text="Could not fetch video information").pack(
                pady=10
            )

        # Options frame
        options_frame = ttk.LabelFrame(dialog, text="Download Options")
        options_frame.pack(fill=tk.X, padx=10, pady=5)

        format_var = tk.StringVar(value="MP4")
        resolution_var = tk.StringVar(value="720")
        playlist_var = tk.StringVar(value="Single video")

        if platform == "YouTube":
            # Playlist options
            if is_youtube_playlist(url):
                playlist_frame = ttk.Frame(options_frame)
                playlist_frame.pack(fill=tk.X, padx=5, pady=2)
                ttk.Radiobutton(
                    playlist_frame,
                    text="Single video",
                    variable=playlist_var,
                    value="Single video",
                ).pack(side=tk.LEFT)
                ttk.Radiobutton(
                    playlist_frame,
                    text="Full playlist",
                    variable=playlist_var,
                    value="Full playlist",
                ).pack(side=tk.LEFT)

            # Format options
            format_frame = ttk.Frame(options_frame)
            format_frame.pack(fill=tk.X, padx=5, pady=2)
            ttk.Radiobutton(
                format_frame, text="Video (MP4)", variable=format_var, value="MP4"
            ).pack(side=tk.LEFT)
            ttk.Radiobutton(
                format_frame, text="Audio (MP3)", variable=format_var, value="MP3"
            ).pack(side=tk.LEFT)

            # Resolution options
            res_frame = ttk.Frame(options_frame)
            res_frame.pack(fill=tk.X, padx=5, pady=2)
            ttk.Label(res_frame, text="Resolution:").pack(side=tk.LEFT)
            for res in ["1080", "720", "480", "360"]:
                ttk.Radiobutton(
                    res_frame, text=f"{res}p", variable=resolution_var, value=res
                ).pack(side=tk.LEFT, padx=(4, 0))

        # Progress frame
        progress_frame = ttk.LabelFrame(dialog, text="Progress")
        progress_frame.pack(fill=tk.X, padx=10, pady=5)

        progress_var = tk.StringVar(value="Ready to download")
        progress_label = ttk.Label(progress_frame, textvariable=progress_var)
        progress_label.pack(pady=5)

        progress_bar = ttk.Progressbar(progress_frame, mode="indeterminate")
        progress_bar.pack(fill=tk.X, padx=5, pady=5)

        def start_download():
            # Hide options and show progress
            options_frame.pack_forget()
            progress_frame.pack(fill=tk.X, pady=(0, 5))

            progress_bar.start()
            progress_var.set("Downloading...")

            final_url = url
            if (
                platform == "YouTube"
                and is_youtube_playlist(url)
                and playlist_var.get() == "Single video"
            ):
                url_parts = url.split("&list=")
                if len(url_parts) > 0:
                    final_url = url_parts[0]

            def download_callback(status, msg_type):
                if not dialog.winfo_exists():
                    return

                progress_bar.stop()
                if msg_type == "success":
                    progress_var.set("Download completed!")
                    self.show_success_notification(f"Download completed for {platform}")
                    # Refresh history after successful download
                    self.refresh_history_view()
                    dialog.after(2000, dialog.destroy)
                elif msg_type == "error":
                    progress_var.set(f"Error: {status}")
                    # Show retry/close buttons
                    retry_button = ttk.Button(
                        progress_frame,
                        text="Retry",
                        command=lambda: [
                            progress_frame.pack_forget(),
                            start_download(),
                        ],
                    )
                    retry_button.pack(side=tk.LEFT, padx=5, pady=5)
                    close_button = ttk.Button(
                        progress_frame, text="Close", command=dialog.destroy
                    )
                    close_button.pack(side=tk.RIGHT, padx=5, pady=5)

            threading.Thread(
                target=download_media,
                args=(
                    final_url,
                    platform,
                    format_var.get(),
                    resolution_var.get() if format_var.get() == "MP4" else None,
                    download_callback,
                ),
                daemon=True,
            ).start()

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(button_frame, text="Download", command=start_download).pack(
            side=tk.LEFT, padx=(0, 5)
        )
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(
            side=tk.LEFT
        )

    def show_notification(self, title, message):
        """Show a notification"""
        if not config.get("notifications_enabled", True):
            return

        try:
            if self.tray_icon:
                self.tray_icon.notify(title, message)
        except Exception as e:
            log(f"Error showing notification: {e}")

    def show_download_banner(self, url, platform):
        """Show a small banner dialog for download options, without fetching video info first."""
        banner = tk.Toplevel()
        banner.title(f"Download {platform} Content")
        banner.geometry("380x220")  # Adjusted height
        banner.resizable(False, False)
        banner.lift()
        banner.attributes("-topmost", True)

        # Center
        banner.update_idletasks()
        x = (banner.winfo_screenwidth() // 2) - (380 // 2)
        y = (banner.winfo_screenheight() // 2) - (220 // 2)  # Adjusted height
        banner.geometry(f"380x220+{x}+{y}")

        main_frame = ttk.Frame(banner)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # URL and Title
        ttk.Label(
            main_frame, text=f"{platform} URL Detected", font=("Arial", 11, "bold")
        ).pack(pady=(0, 5))
        url_display = url[:45] + "..." if len(url) > 45 else url
        ttk.Label(main_frame, text=url_display, wraplength=340, font=("Arial", 8)).pack(
            pady=(0, 10)
        )

        # --- Frames ---
        options_frame = ttk.LabelFrame(main_frame, text="Download Options")
        options_frame.pack(fill=tk.X, pady=(0, 5))
        progress_frame = ttk.LabelFrame(main_frame, text="Progress")
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        # --- Variables ---
        format_var = tk.StringVar(value="MP4")
        resolution_var = tk.StringVar(value="720")
        playlist_var = tk.StringVar(value="Single video")

        # --- Populate Download Options Immediately ---
        if platform == "YouTube":
            # Format
            f_frame = ttk.Frame(options_frame)
            f_frame.pack(fill=tk.X, padx=5, pady=2)
            ttk.Label(f_frame, text="Format:", font=("Arial", 8)).pack(side=tk.LEFT)
            ttk.Radiobutton(f_frame, text="MP4", variable=format_var, value="MP4").pack(
                side=tk.LEFT, padx=(8, 4)
            )
            ttk.Radiobutton(f_frame, text="MP3", variable=format_var, value="MP3").pack(
                side=tk.LEFT, padx=(4, 0)
            )
            # Quality
            q_frame = ttk.Frame(options_frame)
            q_frame.pack(fill=tk.X, padx=5, pady=2)
            ttk.Label(q_frame, text="Quality:", font=("Arial", 8)).pack(side=tk.LEFT)
            for res in ["1080", "720", "480", "360"]:
                ttk.Radiobutton(
                    q_frame, text=f"{res}p", variable=resolution_var, value=res
                ).pack(side=tk.LEFT, padx=(4, 0))
            # Playlist
            if is_youtube_playlist(url):
                p_frame = ttk.Frame(options_frame)
                p_frame.pack(fill=tk.X, padx=5, pady=2)
                ttk.Label(p_frame, text="Playlist:", font=("Arial", 8)).pack(
                    side=tk.LEFT
                )
                ttk.Radiobutton(
                    p_frame,
                    text="Single",
                    variable=playlist_var,
                    value="Single video",
                ).pack(side=tk.LEFT, padx=(8, 4))
                ttk.Radiobutton(
                    p_frame,
                    text="Full",
                    variable=playlist_var,
                    value="Full playlist",
                ).pack(side=tk.LEFT, padx=(4, 0))
        else:
            ttk.Label(
                options_frame,
                text=f"Content will be downloaded as is.",
                font=("Arial", 8),
            ).pack(pady=5)

        # --- Download Function ---
        def start_download():
            # Hide the banner immediately when download is clicked
            banner.withdraw()

            options_frame.pack_forget()
            button_frame.pack_forget()
            progress_frame.pack(fill=tk.X, pady=(0, 5))
            progress_bar.start()
            progress_var.set("Downloading...")

            final_url = url
            if (
                platform == "YouTube"
                and is_youtube_playlist(url)
                and playlist_var.get() == "Single video"
            ):
                final_url = url.split("&list=")[0]

            def download_callback(status, msg_type):
                if not banner.winfo_exists():
                    return
                progress_bar.stop()
                if msg_type == "success":
                    progress_var.set("Download completed!")
                    self.show_success_notification("Download completed successfully")
                    # Refresh history after successful download
                    self.refresh_history_view()
                    banner.after(2000, banner.destroy)
                else:
                    progress_var.set(f"Error: {status}")
                    ttk.Button(
                        progress_frame, text="Close", command=banner.destroy
                    ).pack(pady=5)

            threading.Thread(
                target=download_media,
                args=(
                    final_url,
                    platform,
                    format_var.get(),
                    resolution_var.get(),
                    download_callback,
                ),
                daemon=True,
            ).start()

        # --- Buttons ---
        ttk.Button(button_frame, text="Download", command=start_download).pack(
            side=tk.LEFT, padx=(0, 5)
        )
        ttk.Button(
            button_frame,
            text="Main Window",
            command=lambda: [self.show_window(), banner.destroy()],
        ).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Cancel", command=banner.destroy).pack(
            side=tk.RIGHT
        )

        # --- Progress Bar Widgets ---
        progress_var = tk.StringVar(value="Ready to download")
        ttk.Label(progress_frame, textvariable=progress_var, font=("Arial", 8)).pack(
            pady=3
        )
        progress_bar = ttk.Progressbar(progress_frame, mode="indeterminate")
        progress_bar.pack(fill=tk.X, padx=5, pady=3)

    def show_success_notification(self, message):
        """Show a success notification"""
        if not config.get("notifications_enabled", True):
            return

        try:
            if self.tray_icon:
                self.tray_icon.notify("Download Started", message)
        except Exception as e:
            log(f"Error showing success notification: {e}")

    def hide_to_tray(self):
        """Hide window to system tray"""
        self.hide_thumbnail_tooltip()  # Hide any open tooltip
        self.root.withdraw()
        if self.tray_icon:
            self.tray_icon.visible = True

    def show_window(self, icon=None, item=None):
        """Show the main window"""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        if self.tray_icon:
            self.tray_icon.visible = False

    def quit_app(self, icon=None, item=None):
        """Quit the application"""
        # Stop thumbnail preloading
        self.stop_thumbnail_preload()

        if self.tray_icon:
            self.tray_icon.stop()
        self.root.quit()
        self.root.destroy()

    # Menu Methods
    def new_download(self):
        """Focus on URL input for new download"""
        # Clear the URL field and focus on it
        self.url_var.set("")
        # Scroll to the URL input section
        self.notebook.select(0)  # Switch to first tab

    def export_history(self):
        """Export download history to file"""
        if not self.history:
            messagebox.showinfo("Export History", "No history to export.")
            return

        file_path = filedialog.asksaveasfilename(
            title="Export History",
            defaultextension=".json",
            filetypes=[
                ("JSON files", "*.json"),
                ("CSV files", "*.csv"),
                ("Text files", "*.txt"),
            ],
        )

        if file_path:
            try:
                if file_path.endswith(".json"):
                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(self.history, f, indent=2, ensure_ascii=False)
                elif file_path.endswith(".csv"):
                    import csv

                    with open(file_path, "w", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f)
                        writer.writerow(
                            ["Platform", "Title", "URL", "Format", "File Path", "Date"]
                        )
                        for entry in self.history:
                            from datetime import datetime

                            date = datetime.fromtimestamp(
                                entry.get("timestamp", 0)
                            ).strftime("%Y-%m-%d %H:%M:%S")
                            writer.writerow(
                                [
                                    entry.get("platform", ""),
                                    entry.get("title", ""),
                                    entry.get("url", ""),
                                    entry.get("format", ""),
                                    entry.get("file_path", ""),
                                    date,
                                ]
                            )
                else:  # .txt
                    with open(file_path, "w", encoding="utf-8") as f:
                        for entry in self.history:
                            from datetime import datetime

                            date = datetime.fromtimestamp(
                                entry.get("timestamp", 0)
                            ).strftime("%Y-%m-%d %H:%M:%S")
                            f.write(f"Platform: {entry.get('platform', '')}\n")
                            f.write(f"Title: {entry.get('title', '')}\n")
                            f.write(f"URL: {entry.get('url', '')}\n")
                            f.write(f"Format: {entry.get('format', '')}\n")
                            f.write(f"File: {entry.get('file_path', '')}\n")
                            f.write(f"Date: {date}\n")
                            f.write("-" * 50 + "\n")

                messagebox.showinfo(
                    "Export Complete", f"History exported to:\n{file_path}"
                )
            except Exception as e:
                messagebox.showerror(
                    "Export Error", f"Failed to export history:\n{str(e)}"
                )

    def export_logs_menu(self):
        """Export logs from menu"""
        if not log_buffer:
            messagebox.showinfo("Export Logs", "No logs to export.")
            return

        file_path = filedialog.asksaveasfilename(
            title="Export Logs",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )

        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    for entry in log_buffer:
                        f.write(entry + "\n")
                messagebox.showinfo(
                    "Export Complete", f"Logs exported to:\n{file_path}"
                )
            except Exception as e:
                messagebox.showerror(
                    "Export Error", f"Failed to export logs:\n{str(e)}"
                )

    def import_settings(self):
        """Import settings from file"""
        file_path = filedialog.askopenfilename(
            title="Import Settings",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )

        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    imported_config = json.load(f)

                # Validate and merge settings
                for key, value in imported_config.items():
                    if key in DEFAULT_CONFIG:
                        config[key] = value

                save_config(config)

                # Update UI to reflect imported settings
                self.path_var.set(config["base_dir"])
                self.monitor_var.set(config.get("auto_monitor", True))
                self.notifications_var.set(config.get("notifications_enabled", True))
                self.thumbnail_var.set(config.get("show_thumbnails", True))
                self.logging_var.set(config.get("logging_enabled", False))

                create_directories()
                messagebox.showinfo(
                    "Import Complete", "Settings imported successfully!"
                )

            except Exception as e:
                messagebox.showerror(
                    "Import Error", f"Failed to import settings:\n{str(e)}"
                )

    def export_settings(self):
        """Export current settings to file"""
        file_path = filedialog.asksaveasfilename(
            title="Export Settings",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )

        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=2)
                messagebox.showinfo(
                    "Export Complete", f"Settings exported to:\n{file_path}"
                )
            except Exception as e:
                messagebox.showerror(
                    "Export Error", f"Failed to export settings:\n{str(e)}"
                )

    def show_preferences(self):
        """Show preferences dialog"""
        prefs_window = tk.Toplevel(self.root)
        prefs_window.title("Preferences")
        prefs_window.geometry("500x400")
        prefs_window.transient(self.root)
        prefs_window.grab_set()

        center_window(prefs_window, 500, 400)

        # Main frame
        main_frame = ttk.Frame(prefs_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Download paths
        ttk.Label(main_frame, text="Download Paths", font=("Arial", 10, "bold")).pack(
            pady=(0, 10)
        )

        # Base directory
        base_frame = ttk.Frame(main_frame)
        base_frame.pack(fill=tk.X, pady=5)
        ttk.Label(base_frame, text="Base Directory:").pack(side=tk.LEFT)
        base_entry = ttk.Entry(base_frame, textvariable=self.path_var, width=40)
        base_entry.pack(side=tk.LEFT, padx=(10, 5), fill=tk.X, expand=True)
        ttk.Button(base_frame, text="Browse", command=self.browse_path).pack(
            side=tk.RIGHT
        )

        # Behavior settings
        ttk.Label(main_frame, text="Behavior", font=("Arial", 10, "bold")).pack(
            pady=(20, 10)
        )

        behavior_frame = ttk.Frame(main_frame)
        behavior_frame.pack(fill=tk.X)

        ttk.Checkbutton(
            behavior_frame, text="Auto-monitor clipboard", variable=self.monitor_var
        ).pack(anchor="w", pady=2)
        ttk.Checkbutton(
            behavior_frame, text="Enable notifications", variable=self.notifications_var
        ).pack(anchor="w", pady=2)
        ttk.Checkbutton(
            behavior_frame, text="Show thumbnails on hover", variable=self.thumbnail_var
        ).pack(anchor="w", pady=2)
        ttk.Checkbutton(
            behavior_frame, text="Enable debug logging", variable=self.logging_var
        ).pack(anchor="w", pady=2)

        # Buttons
        button_frame = ttk.Frame(prefs_window)
        button_frame.pack(fill=tk.X, padx=20, pady=20)

        def apply_settings():
            config["base_dir"] = self.path_var.get()
            config["yt_mp3_dir"] = str(Path(self.path_var.get()) / "YouTube" / "MP3")
            config["yt_mp4_dir"] = str(Path(self.path_var.get()) / "YouTube" / "MP4")
            config["insta_dir"] = str(Path(self.path_var.get()) / "Instagram")
            config["tiktok_dir"] = str(Path(self.path_var.get()) / "TikTok")
            config["auto_monitor"] = self.monitor_var.get()
            config["notifications_enabled"] = self.notifications_var.get()
            config["show_thumbnails"] = self.thumbnail_var.get()
            config["logging_enabled"] = self.logging_var.get()
            save_config(config)
            create_directories()
            prefs_window.destroy()
            self.status_var.set("Settings saved")

        ttk.Button(button_frame, text="Apply", command=apply_settings).pack(
            side=tk.RIGHT, padx=(5, 0)
        )
        ttk.Button(button_frame, text="Cancel", command=prefs_window.destroy).pack(
            side=tk.RIGHT
        )

    def clear_history_menu(self):
        """Clear download history from menu"""
        if not self.history:
            messagebox.showinfo("Clear History", "History is already empty.")
            return

        result = messagebox.askyesno(
            "Clear History",
            f"Are you sure you want to clear all {len(self.history)} history entries?\n\nThis action cannot be undone.",
        )

        if result:
            self.history.clear()
            save_history([])
            self.populate_history()
            self.status_var.set("History cleared")

    def clear_logs_menu(self):
        """Clear logs from menu"""
        if not log_buffer:
            messagebox.showinfo("Clear Logs", "No logs to clear.")
            return

        result = messagebox.askyesno(
            "Clear Logs", "Are you sure you want to clear all log entries?"
        )
        if result:
            log_buffer.clear()
            self.status_var.set("Logs cleared")

    def open_downloads_folder(self):
        """Open the downloads folder in file explorer"""
        try:
            downloads_path = Path(config["base_dir"])
            if downloads_path.exists():
                if sys.platform == "win32":
                    os.startfile(downloads_path)
                elif sys.platform == "darwin":  # macOS
                    subprocess.run(["open", downloads_path])
                else:  # linux
                    subprocess.run(["xdg-open", downloads_path])
            else:
                messagebox.showwarning(
                    "Folder Not Found", f"Downloads folder not found:\n{downloads_path}"
                )
        except Exception as e:
            messagebox.showerror("Error", f"Could not open downloads folder:\n{e}")

    def check_for_updates(self):
        """Check for application updates"""
        messagebox.showinfo(
            "Check for Updates",
            "Update checking is not implemented yet.\n\nPlease check the GitHub repository manually for updates.",
        )

    def show_about(self):
        """Show about dialog"""
        about_window = tk.Toplevel(self.root)
        about_window.title("About G-Downloader")
        about_window.geometry("550x400")
        about_window.resizable(False, False)
        about_window.transient(self.root)
        about_window.grab_set()

        center_window(about_window, 450, 400)

        # Main frame
        main_frame = ttk.Frame(about_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # App icon (if available)
        try:
            icon_image = Image.open("./icon.ico")
            icon_image = icon_image.resize((64, 64), Image.Resampling.LANCZOS)
            icon_photo = ImageTk.PhotoImage(icon_image)
            icon_label = tk.Label(main_frame, image=icon_photo)
            icon_label.image = icon_photo  # Keep reference
            icon_label.pack(pady=10)
        except:
            pass

        # App info
        tk.Label(main_frame, text="G-Downloader", font=("Arial", 16, "bold")).pack(
            pady=5
        )
        tk.Label(
            main_frame, text="Media Downloader with Auto-Detection", font=("Arial", 10)
        ).pack(pady=5)
        tk.Label(main_frame, text="Version 1.0", font=("Arial", 9)).pack(pady=5)

        # Developer info
        tk.Label(
            main_frame, text="Developed by Ghassan Elgendy", font=("Arial", 10, "bold")
        ).pack(pady=(15, 5))

        # GitHub link
        github_label = tk.Label(
            main_frame,
            text="Visit my GitHub page",
            font=("Arial", 9),
            fg="blue",
            cursor="hand2",
        )
        github_label.pack(pady=2)

        # Make the GitHub link clickable
        def open_github(event):
            import webbrowser

            webbrowser.open("https://github.com/ghassanelgendy")

        github_label.bind("<Button-1>", open_github)

        # Features
        features_text = """Features:
• Auto-detect YouTube, Instagram, TikTok URLs
• Download in various formats (MP3, MP4)
• Thumbnail generation and preview
• Download history with file management
• Clipboard monitoring
• System tray integration"""

        tk.Label(
            main_frame, text=features_text, font=("Arial", 8), justify=tk.LEFT
        ).pack(pady=15)

        # Powered by
        tk.Label(
            main_frame, text="Powered by yt-dlp", font=("Arial", 8, "italic")
        ).pack(pady=5)

        # Close button
        ttk.Button(main_frame, text="Close", command=about_window.destroy).pack(pady=15)

    def run(self):
        """Run the application"""
        self.root.mainloop()


if __name__ == "__main__":
    # Check for missing dependencies
    missing_deps = []
    try:
        from PIL import Image, ImageTk
    except ImportError:
        missing_deps.append("Pillow")

    try:
        import requests
    except ImportError:
        missing_deps.append("requests")

    try:
        import pystray
    except ImportError:
        missing_deps.append("pystray")

    if missing_deps:
        log(f"Missing dependencies: {', '.join(missing_deps)}")
        root = tk.Tk()
        root.withdraw()

        deps_text = "\n".join([f"• {dep}" for dep in missing_deps])
        result = messagebox.askyesno(
            "Missing Dependencies",
            f"The following dependencies are missing:\n\n{deps_text}\n\n"
            "Would you like to install them now?\n\n"
            "Note: This will run 'pip install -r requirements.txt' in the terminal.",
        )

        if result:
            try:
                import subprocess

                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                    check=True,
                )
                messagebox.showinfo(
                    "Installation Complete",
                    "Dependencies installed successfully!\n\nPlease restart the application.",
                )
            except Exception as e:
                messagebox.showerror(
                    "Installation Failed",
                    f"Failed to install dependencies:\n{str(e)}\n\n"
                    "Please install them manually by running:\n"
                    "pip install -r requirements.txt",
                )
        else:
            messagebox.showinfo(
                "Installation Skipped",
                "Please install the missing dependencies manually:\n\n"
                "pip install -r requirements.txt",
            )

        root.destroy()
        sys.exit(1)

    # Check if yt-dlp exists at startup
    if not Path(YTDLP_PATH).exists():
        log(f"CRITICAL ERROR: yt-dlp.exe not found at {YTDLP_PATH}")
        root = tk.Tk()
        root.withdraw()
        tk.messagebox.showerror(
            "Startup Error",
            f"yt-dlp.exe not found at the specified path:\n{YTDLP_PATH}\n\nPlease check the YTDLP_PATH variable in the script.",
        )
        sys.exit(1)

    # Create and run the application
    app = MainApplication()
    app.run()
