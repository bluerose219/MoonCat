@echo off
rem Build MoonCat into a single executable: dist\MoonCat.exe
rem When run as an exe, saves go to %APPDATA%\MoonCat
cd /d "%~dp0"
python -m pip install --upgrade pyinstaller || goto :error
python -m PyInstaller --noconfirm --onefile --windowed --name MoonCat --add-data "game\assets;game\assets" main.py || goto :error
echo.
echo Done: dist\MoonCat.exe
exit /b 0

:error
echo Build failed.
exit /b 1
