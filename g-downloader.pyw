import os
import time
import re
import threading
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import sys
import shutil


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

# Access the Windows Downloads folder
try:
    downloads_folder = Path(os.path.expanduser("~/Downloads"))
    base_dir = downloads_folder / "g-downloader"
    yt_mp3_dir = base_dir / "YouTube" / "MP3"
    yt_mp4_dir = base_dir / "YouTube" / "MP4"
    insta_dir = base_dir / "Instagram"
    tiktok_dir = base_dir / "TikTok"

    # Ensure folders exist
    for folder in [yt_mp3_dir, yt_mp4_dir, insta_dir, tiktok_dir]:
        folder.mkdir(parents=True, exist_ok=True)
except Exception as e:
    # Basic error handling if folders can't be created
    print(f"Error creating directories: {e}")
    # In a .pyw context, this print won't be visible.
    # Consider using tkinter.messagebox for critical startup errors.
    # import tkinter.messagebox
    # tkinter.Tk().withdraw() # Hide root window
    # tkinter.messagebox.showerror("Startup Error", f"Failed to create directories:\n{e}")
    sys.exit(1)  # Exit if essential setup fails


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


# Download logic
def download_media(url, platform, format_choice="MP4", resolution=None):
    print(f"Starting download for: {url}")  # Basic feedback (won't show in pyw)
    cmd = []
    try:
        if not Path(YTDLP_PATH).exists():
            print(f"Error: yt-dlp not found at {YTDLP_PATH}")
            # Maybe show GUI error here
            return

        if platform == "YouTube":
            if format_choice == "MP3":
                output_template = str(yt_mp3_dir / "%(title).80s.%(ext)s")
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
                output_template = str(yt_mp4_dir / "%(title).80s.%(ext)s")
                # Ensure resolution is provided if format is MP4, default if needed
                res_option = (
                    resolution if resolution else "720"
                )  # Default to 720p if None
                format_string = f"bestvideo[ext=mp4][height<={res_option}]+bestaudio[ext=m4a]/best[ext=mp4]/best"  # Added /best fallback
                cmd = [YTDLP_PATH, "-f", format_string, "-o", output_template, url]

        elif platform == "Instagram":
            output_template = str(insta_dir / "%(title).80s.%(ext)s")
            cmd = [YTDLP_PATH, "-f", "best", "-o", output_template, url]

        elif platform == "TikTok":
            output_template = str(tiktok_dir / "%(title).80s.%(ext)s")
            # TikTok-specific options for best quality
            cmd = [
                YTDLP_PATH,
                "--no-check-certificates",  # Sometimes needed for TikTok
                "--no-warnings",
                "-f",
                "best",
                "-o",
                output_template,
                url,
            ]

        else:
            print(f"Unsupported platform: {platform}")
            return

        print(f"Executing command: {' '.join(cmd)}")  # Won't show in pyw
        # Run subprocess without creating a console window
        result = subprocess.run(
            cmd,
            capture_output=True,  # Capture stdout/stderr
            text=True,  # Decode as text
            check=False,  # Don't raise exception on error, check returncode instead
            # --- ADD THIS FLAG ---
            creationflags=CREATE_NO_WINDOW,
        )

        if result.returncode == 0:
            print(f"Download successful: {url}")  # Won't show in pyw
        else:
            # Log or show error (print won't be visible in pyw)
            print(f"Download failed for {url}. Return code: {result.returncode}")
            print(f"stderr: {result.stderr}")
            # Consider tkinter.messagebox.showerror here for user feedback

    except Exception as e:
        print(f"An error occurred during download_media for {url}: {e}")
        # Consider tkinter.messagebox.showerror here


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
            print(
                "Warning: Could not get valid screen/window dimensions for centering."
            )
    except Exception as e:
        print(f"Error centering window: {e}")


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

                print(
                    f"Proceeding to download: {final_url}, Format: {format_choice}, Res: {resolution}"
                )  # Won't show in pyw

                # Start download in a separate thread to keep GUI responsive
                threading.Thread(
                    target=download_media,
                    args=(final_url, platform, format_choice, resolution),
                    daemon=True,  # Allows program to exit even if thread is running
                ).start()
            except Exception as e:
                print(f"Error in proceed function: {e}")
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
        print(f"Error creating prompt window: {e}")


# Clipboard watcher using Windows clipboard directly
def clipboard_monitor():
    last_text = ""
    try:
        last_text = get_clipboard_text()  # Get initial state
    except Exception as e:
        print(f"Error getting initial clipboard content: {e}")
        # Decide whether to continue or exit if clipboard is inaccessible
        # return

    processed_urls = set()  # Keep track of processed URLs to avoid repeats

    print("Clipboard monitor started...")  # Won't show in pyw
    while True:
        try:
            current_text = get_clipboard_text()
            # Check if text changed, is not empty, and hasn't been processed
            if (
                current_text
                and current_text != last_text
                and current_text not in processed_urls
            ):
                print(f"Clipboard changed: {current_text[:50]}...")  # Won't show
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
                    print(f"Detected {platform} URL: {url_to_process}")  # Won't show
                    # Run the GUI prompt. It handles its own threading for download.
                    prompt_download(url_to_process, platform)
                    processed_urls.add(url_to_process)  # Mark as processed

                last_text = (
                    current_text  # Update last_text only after processing change
                )

            # Prevent busy-waiting
            time.sleep(1)  # Check every second

        except KeyboardInterrupt:
            print("Clipboard monitor interrupted.")
            break
        except Exception as e:
            # Log error and continue monitoring if possible
            print(f"Error in clipboard monitoring loop: {e}")
            # Avoid spamming errors if clipboard access is consistently failing
            time.sleep(5)


def get_clipboard_text():
    try:
        # Using powershell to get clipboard content, hide the window
        result = subprocess.run(
            [
                "powershell.exe",
                "-Command",
                "Get-Clipboard -Raw",
            ],  # Use -Raw for cleaner text
            capture_output=True,
            text=True,
            check=True,  # Raise error if PowerShell fails
            encoding="utf-8",  # Explicitly set encoding
            # --- ADD THIS FLAG ---
            creationflags=CREATE_NO_WINDOW,
        )
        return result.stdout.strip()
    except FileNotFoundError:
        print("Error: powershell.exe not found. Cannot monitor clipboard.")
        # This is a critical error for this script's function
        # Maybe raise an exception to stop the monitor thread?
        raise  # Stop the monitor if powershell isn't found
    except subprocess.CalledProcessError as e:
        # Handle cases where clipboard might be empty or inaccessible
        # Get-Clipboard might return error code 1 if clipboard is empty or locked
        # print(f"Powershell Get-Clipboard error (maybe empty or locked?): {e}")
        # print(f"Stderr: {e.stderr}")
        return ""  # Return empty string on error
    except Exception as e:
        print(f"Unexpected error getting clipboard text: {e}")
        return ""  # Return empty string on other errors


if __name__ == "__main__":
    # Create the hidden main Tkinter window
    # This is necessary for Toplevel windows and messageboxes to work correctly
    # without showing an unwanted blank root window.
    root = tk.Tk()
    root.withdraw()

    # Check if yt-dlp exists at startup
    if not Path(YTDLP_PATH).exists():
        print(f"CRITICAL ERROR: yt-dlp.exe not found at {YTDLP_PATH}")
        tk.messagebox.showerror(
            "Startup Error",
            f"yt-dlp.exe not found at the specified path:\n{YTDLP_PATH}\n\nPlease check the YTDLP_PATH variable in the script.",
        )
        sys.exit(1)

    # Start the clipboard monitor in a separate thread
    monitor_thread = threading.Thread(target=clipboard_monitor, daemon=True)
    monitor_thread.start()

    # Keep the main thread alive to serve the GUI toolkit
    # root.mainloop() is essential for Tkinter events (like closing Toplevel windows)
    # and keeps the script running until the root window is destroyed (which it isn't explicitly).
    # The script will exit when the mainloop ends, typically by closing all windows
    # or explicitly calling root.destroy(). Since the root is hidden and daemons are used,
    # closing the prompt windows won't end the script. Need a way to terminate.
    # For now, rely on Ctrl+C in a terminal or Task Manager for the .pyw file.
    # A system tray icon would be a better way to manage a background app.
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\nExiting application.")
