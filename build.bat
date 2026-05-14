@echo off
echo === GPU Pet Monitor - Build Script ===

:: Clean previous
rmdir /s /q build dist 2>nul

:: Find ffi.dll (required by ctypes)
for /f "delims=" %%i in ('python -c "import sys,os;print(os.path.join(sys.prefix,'Library','bin','ffi.dll'))"') do set "FFI_DLL=%%i"

:: Build
pyinstaller --onefile --windowed --noconfirm ^
    --name "GPU-Pet-Monitor" ^
    --add-data "skins;skins" ^
    --add-binary "%FFI_DLL%;." ^
    --hidden-import pynvml ^
    --hidden-import src.animation.procedural_animator ^
    --hidden-import src.skins.skin_manager ^
    --hidden-import src.utils.fonts ^
    --hidden-import src.platform.windows ^
    --exclude-module tkinter ^
    --exclude-module matplotlib ^
    run.py

echo.
echo === Done: dist\GPU-Pet-Monitor.exe ===
dir dist\GPU-Pet-Monitor.exe
