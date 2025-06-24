from distutils.core import setup
import py2exe
import sys
import os

# Include the src directory in the path
sys.path.append("src")

# Data files to include
data_files = [
    ("assets", ["assets/icon.ico"]),
]

# Options for py2exe
options = {
    "py2exe": {
        "bundle_files": 1,  # Bundle everything into one file
        "compressed": True,
        "optimize": 2,
        "includes": [
            "tkinter",
            "tkinter.ttk",
            "tkinter.filedialog",
            "tkinter.messagebox",
            "PIL",
            "PIL.Image",
            "PIL.ImageTk",
            "requests",
            "pystray",
            "threading",
            "subprocess",
            "pathlib",
            "json",
            "time",
            "re",
            "shutil",
            "io",
            "base64",  # Add base64 to includes
        ],
        "excludes": [
            "email",
            "calendar",
            "doctest",
            "ftplib",
            "getpass",
            "getopt",
            "http",
            "imaplib",
            "nntplib",
            "optparse",
            "poplib",
            "smtplib",
            "sqlite3",
            "telnetlib",
            "unittest",
            "urllib",
            "xml",
        ],
        "dll_excludes": ["w9xpopen.exe", "MSVCP90.dll", "MSVCR90.dll"],
    }
}

setup(
    name="G-Downloader",
    version="1.0",
    description="Media downloader for YouTube, Instagram, and TikTok",
    author="Your Name",
    windows=[
        {
            "script": "src/g-downloader.pyw",
            "icon_resources": [(1, "assets/icon.ico")],
            "dest_base": "g-downloader",
        }
    ],
    data_files=data_files,
    options=options,
    zipfile=None,  # Bundle everything into the exe
)
