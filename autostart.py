"""Windows 开机自启管理 — HKCU Run 注册表方式"""

import os
import sys
import winreg


REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
REG_NAME = "VoiceInput"


def _get_command() -> str:
    """返回当前程序路径，用于注册自启"""
    # PyInstaller 打包的 exe
    if getattr(sys, "frozen", False):
        return sys.executable

    # 脚本模式: 用 pythonw.exe 避免控制台窗口
    script = os.path.abspath(sys.argv[0])
    exe = sys.executable.replace("python.exe", "pythonw.exe")
    if not os.path.exists(exe):
        exe = sys.executable  # fallback
    return f'"{exe}" "{script}"'


def is_enabled() -> bool:
    """检查是否已开启自启"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, REG_NAME)
            return True
    except FileNotFoundError:
        return False


def enable() -> None:
    """开启开机自启"""
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, REG_NAME, 0, winreg.REG_SZ, _get_command())


def disable() -> None:
    """关闭开机自启"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, REG_NAME)
    except FileNotFoundError:
        pass
