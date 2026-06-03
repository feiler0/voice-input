@echo off
title Voice Input - 启动诊断
cd /d "%~dp0"
echo.
echo ========================================
echo   Voice Input 启动诊断
echo ========================================
echo.
echo [1] 工作目录: %cd%
echo [2] pythonw 路径:
where pythonw 2>&1
echo.
echo [3] 启动 Voice Input...
echo.

start "VoiceInput" pythonw -u main.py

echo [4] 启动命令已执行，等待 3 秒检查进程...
timeout /t 3 /nobreak >nul

echo.
echo [5] 检查 python 进程:
tasklist /fi "imagename eq pythonw.exe" 2>&1 | findstr /i "pythonw" >nul
if %errorlevel% equ 0 (
    echo     pythonw.exe 运行中 - 启动成功！
    echo     请在任务栏右下角系统托盘找到绿色圆点图标。
    echo     按住 右Ctrl 开始说话，松开自动识别粘贴。
) else (
    echo     pythonw.exe 未找到 - 启动失败！
    echo     请检查 app.log 日志排查错误。
)

echo.
echo ========================================
pause
