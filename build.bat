@echo off
REM Voice Input - 打包脚本
REM 运行此脚本前确保已安装: pip install pyinstaller

echo Building Voice Input executable...

pyinstaller --onedir ^
    --windowed ^
    --name "VoiceInput" ^
    --noconfirm ^
    --add-data "README.md;." ^
    --hidden-import "pynput.keyboard._win32" ^
    --hidden-import "pynput.mouse._win32" ^
    --hidden-import "sounddevice" ^
    --hidden-import "funasr" ^
    --hidden-import "modelscope" ^
    --hidden-import "PySide6" ^
    --collect-submodules "PySide6" ^
    --collect-all "funasr" ^
    main.py

echo.
echo Done! Executable in dist\VoiceInput\VoiceInput.exe
