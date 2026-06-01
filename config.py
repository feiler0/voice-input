"""配置管理 — JSON 配置文件读写"""

import json
import os
from pathlib import Path


# 配置文件路径: %APPDATA%/voice-input/config.json (Windows)
# 或 ~/.config/voice-input/config.json (Linux/Mac)
def _get_config_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path.home() / ".config"
    return base / "voice-input"


CONFIG_DIR = _get_config_dir()
CONFIG_PATH = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "device": None,              # 输入设备索引 (None = 默认)
    "hotkey": "ctrl_r",          # PTT 热键 (pynput key name)
    "auto_paste": True,          # 是否自动粘贴
    "model": "",
    "auto_start": False,
}


def load_config() -> dict:
    """加载配置，不存在则返回默认值"""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except (json.JSONDecodeError, OSError):
            return dict(DEFAULT_CONFIG)
    return dict(DEFAULT_CONFIG)


def save_config(cfg: dict) -> None:
    """保存配置"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
