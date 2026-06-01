# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Voice Input desktop app"""

import os
import sys

# ─── 排除不必要的模块 ────────────────────────────────────

EXCLUDES = [
    # torch (已不需要, 用 sherpa-onnx 替代)
    "torch",
    "funasr",
    "modelscope",
    # CUDA
    "nvidia",
    "cuda",
    # PySide6 无用组件 (节省 ~100MB)
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtWebChannel",
    "PySide6.QtQuick",
    "PySide6.QtQml",
    "PySide6.QtQuick3D",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DRender",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic",
    "PySide6.Qt3DExtras",
    "PySide6.QtBluetooth",
    "PySide6.QtNfc",
    "PySide6.QtPositioning",
    "PySide6.QtSensors",
    "PySide6.QtMultimedia",
    "PySide6.QtSerialPort",
    "PySide6.QtSql",
    "PySide6.QtTest",
    "PySide6.QtXml",
    "PySide6.QtHelp",
    "PySide6.QtSpatialAudio",
    # 开发/测试工具
    "setuptools",
    "pkg_resources",
    "matplotlib",
    "IPython",
    "jupyter",
    "notebook",
    # 文档/字体
    "docutils",
    "PIL",
]

# ─── 构建 ─────────────────────────────────────────────────

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        "sherpa_onnx",
        "win32api",
        "win32event",
        "win32gui",
        "win32process",
        "win32con",
        "winerror",
        "numpy",
        "sounddevice",
        "pynput",
        "pyperclip",
        "pyautogui",
    ],
    hookspath=[],
    hooksconfig={},
    excludes=EXCLUDES,
    runtime_hooks=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="VoiceInput",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
