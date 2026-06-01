"""剪贴板输出模块 — 复制文字 + 模拟粘贴"""

import time
import pyperclip
import pyautogui


def copy_and_paste(text: str, auto_paste: bool = True) -> bool:
    """复制文字到剪贴板，并模拟 Ctrl+V 粘贴

    Args:
        text: 要粘贴的文字
        auto_paste: 是否自动触发粘贴

    Returns:
        True 成功，False 失败
    """
    if not text:
        return False

    try:
        # 复制到剪贴板
        pyperclip.copy(text)

        if auto_paste:
            # 等一小会儿确保剪贴板写入了
            time.sleep(0.05)
            # 模拟 Ctrl+V (Windows/Linux) 或 Cmd+V (Mac)
            pyautogui.hotkey("ctrl", "v")

        return True

    except Exception as e:
        print(f"[clipboard] Error: {e}")
        return False


def copy_only(text: str) -> bool:
    """仅复制到剪贴板，不粘贴"""
    return copy_and_paste(text, auto_paste=False)
