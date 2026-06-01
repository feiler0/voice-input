"""启动诊断 — 捕捉启动瞬间的弹窗"""
import os, sys, time, threading, subprocess

# 设置环境变量
os.environ["MODELSCOPE_DISABLE_BROWSER"] = "1"
os.environ["MODELSCOPE_ACCEPT_LICENSE"] = "true"

# 截屏函数
def burst_screenshots(interval=0.2, count=30):
    """启动后连续截屏，捕捉一闪而过的弹窗"""
    import win32gui, win32ui, win32con, win32api
    from PIL import Image

    out_dir = os.path.join(os.path.dirname(__file__), "screenshots")
    os.makedirs(out_dir, exist_ok=True)

    time.sleep(1)  # 等 QApplication 初始化
    for i in range(count):
        try:
            hwnd = win32gui.GetDesktopWindow()
            dc = win32gui.GetDC(hwnd)
            dc_obj = win32ui.CreateDCFromHandle(dc)
            compat_dc = dc_obj.CreateCompatibleDC()

            width = win32api.GetSystemMetrics(0)
            height = win32api.GetSystemMetrics(1)

            bitmap = win32ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(dc_obj, width, height)
            compat_dc.SelectObject(bitmap)
            compat_dc.BitBlt((0, 0), (width, height), dc_obj, (0, 0), win32con.SRCCOPY)

            bitmap_info = bitmap.GetInfo()
            bitmap_str = bitmap.GetBitmapBits(True)
            img = Image.frombuffer("RGBA", (bitmap_info['bmWidth'], bitmap_info['bmHeight']), bitmap_str, "raw", "BGRA", 0, 1)
            img.save(os.path.join(out_dir, f"shot_{i:03d}.png"))

            dc_obj.DeleteDC()
            compat_dc.DeleteDC()
            win32gui.ReleaseDC(hwnd, dc)
        except Exception as e:
            print(f"Shot {i} failed: {e}")
        time.sleep(interval)

    print(f"Screenshots saved to {out_dir}")
    return out_dir


def main():
    print("[diag] Starting diagnostic startup...")

    # Step 1: 轻量启动 — 只创建 QApplication
    print("[diag] Step 1: QApplication...")
    from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
    from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
    from PySide6.QtCore import Qt, QTimer

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    print(f"[diag] QApplication created at {time.time():.3f}")

    # 启动截屏线程
    screen_thread = threading.Thread(target=burst_screenshots, daemon=True)
    screen_thread.start()

    # Step 2: 导入配置
    print(f"[diag] Step 2: config at {time.time():.3f}")
    from config import load_config
    config = load_config()

    # Step 3: 导入 recorder
    print(f"[diag] Step 3: recorder at {time.time():.3f}")
    from recorder import VoiceRecorder
    recorder = VoiceRecorder(device=config.get("device"))

    # Step 4: 导入 engine
    print(f"[diag] Step 4: engine at {time.time():.3f}")
    from engine import ASREngine
    engine = ASREngine(model_name=config.get("model", "small"))

    # Step 5: 创建托盘
    print(f"[diag] Step 5: tray at {time.time():.3f}")
    pix = QPixmap(64, 64)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setBrush(QColor("#22c55e"))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(8, 8, 48, 48)
    painter.end()
    icon = QIcon(pix)

    tray = QSystemTrayIcon(icon, app)
    tray.setToolTip("Voice Input Diagnostic")
    menu = QMenu()
    menu.addAction("退出", app.quit)
    tray.setContextMenu(menu)
    tray.show()

    # Step 6: 后台加载模型
    print(f"[diag] Step 6: loading model at {time.time():.3f}")
    def _load():
        engine.load()
        print(f"[diag] Model loaded at {time.time():.3f}")
    threading.Thread(target=_load, daemon=True).start()

    # Step 7: pynput 热键
    print(f"[diag] Step 7: hotkey at {time.time():.3f}")
    from pynput import keyboard as kb
    ptt_key = getattr(kb.Key, config.get("hotkey", "ctrl_r"))
    def on_press(key):
        if key == ptt_key:
            print("[diag] PTT pressed")
    def on_release(key):
        if key == ptt_key:
            print("[diag] PTT released")
    threading.Thread(target=lambda: kb.Listener(on_press=on_press, on_release=on_release).run(), daemon=True).start()

    print(f"[diag] All ready at {time.time():.3f}")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
