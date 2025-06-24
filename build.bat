@echo off
echo Building G-Downloader with py2exe...
echo.

REM Clean previous builds
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM Install py2exe if not already installed
pip install py2exe

REM Build the executable
python setup.py py2exe

echo.
echo Build complete! Check the 'dist' folder for your executable.
echo.
pause 