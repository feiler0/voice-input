"""Voice Input — 录音转文字桌面工具 (PTT 模式)

按住热键录音 → 松开 → whisper 转文字 → 自动粘贴
"""

import os
import sys
import time
import threading
import subprocess
import win32event
import win32api
import winerror
from typing import Optional

# ── 防止控制台窗口闪烁 ────────────────────────────────────
# 当 pythonw.exe（GUI 模式）生成 ffmpeg.exe 等控制台子进程时，
# Windows 会短暂显示一个控制台窗口，看起来像"网页弹窗"。
# 此补丁自动添加 CREATE_NO_WINDOW 标志到所有子进程调用。

_original_popen_init = subprocess.Popen.__init__


def _silent_popen_init(self, *args, **kwargs):
    kwargs.setdefault("creationflags", 0)
    kwargs["creationflags"] |= subprocess.CREATE_NO_WINDOW  # 0x08000000
    return _original_popen_init(self, *args, **kwargs)


subprocess.Popen.__init__ = _silent_popen_init

from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QLabel
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QCursor
from PySide6.QtCore import QObject, Signal, Qt, QTimer


# ─── 图标 ────────────────────────────────────────────────

def _make_pixmap(color: str, size: int = 64) -> QPixmap:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor(color))
    painter.setPen(Qt.NoPen)
    m = size // 8
    painter.drawEllipse(m, m, size - 2 * m, size - 2 * m)
    painter.end()
    return pix


ICONS: dict[str, QIcon] = {}

def _get_icons() -> dict[str, QIcon]:
    if not ICONS:
        ICONS["idle"] = QIcon(_make_pixmap("#22c55e"))
        ICONS["recording"] = QIcon(_make_pixmap("#ef4444"))
        ICONS["transcribing"] = QIcon(_make_pixmap("#f59e0b"))
        ICONS["error"] = QIcon(_make_pixmap("#6b7280"))
    return ICONS


# ─── 光标指示器 ──────────────────────────────────────────

class RecordingIndicator(QLabel):
    """跟随光标的小圆点指示器"""

    def __init__(self):
        super().__init__(None)
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setStyleSheet("background: transparent;")
        self.setFixedSize(16, 16)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._follow_cursor)
        self._visible = False
        self.hide()

    def show_recording(self):
        self.setText("🔴")
        self.setFont(QFont("Segoe UI", 10))
        self.setFixedSize(16, 16)
        self._follow_cursor()
        self.show()
        self.raise_()
        self._visible = True
        self._timer.start(50)

    def show_transcribing(self):
        self.setText("🟡")
        self.setFont(QFont("Segoe UI", 10))
        self.setFixedSize(16, 16)

    def hide_indicator(self):
        self._visible = False
        self._timer.stop()
        self.hide()

    def _follow_cursor(self):
        if not self._visible:
            return
        pos = QCursor.pos()
        self.move(pos.x() + 12, pos.y() - 10)


# ─── 信号桥 ──────────────────────────────────────────────

class StatusSignals(QObject):
    status_changed = Signal(str)


# ─── 主应用 ─────────────────────────────────────────────

class VoiceInputApp:
    def __init__(self):
        from config import load_config

        self.config = load_config()
        self.signals = StatusSignals()
        self.recorder = None
        self.engine = None
        self.punctuation = None
        self.tray = None
        self.indicator = None
        self.settings_window = None
        self._status = "idle"
        self._record_thread: Optional[threading.Thread] = None
        self._pending_recording = False
        self._loading_anim_timer: Optional[QTimer] = None
        self._loading_anim_frame = 0
        self.signals.status_changed.connect(self._on_status_changed)

    def set_status(self, status: str) -> None:
        self.signals.status_changed.emit(status)

    def _on_status_changed(self, status: str) -> None:
        self._status = status
        icons = _get_icons()
        if self.tray:
            m = {
                "idle": icons["idle"], "ready": icons["idle"],
                "recording": icons["recording"], "transcribing": icons["transcribing"],
                "done": icons["idle"], "error": icons["error"],
            }
            self.tray.setIcon(m.get(status, icons["idle"]))

        # 模型加载完成/失败 → 停止 loading 动画
        if status in ("ready", "error"):
            if self._loading_anim_timer:
                self._loading_anim_timer.stop()
                self._loading_anim_timer = None
        if status == "ready":
            if self.tray:
                self.tray.setToolTip("Voice Input — 按住 PTT 键说话")
            if self._pending_recording:
                self._pending_recording = False
                self.start_recording()
        elif status == "error":
            if self.tray:
                self.tray.setToolTip("Voice Input — 模型加载失败，请检查安装")

        if status == "recording":
            if self.indicator is None:
                self.indicator = RecordingIndicator()
            self.indicator.show_recording()
        elif status == "transcribing":
            if self.indicator is None:
                self.indicator = RecordingIndicator()
            self.indicator.show_transcribing()
        elif status in ("idle", "done", "error") and self.indicator:
            self.indicator.hide_indicator()

    def _on_recorder_status(self, status: str) -> None:
        self.set_status(status)

    def _on_engine_status(self, status: str) -> None:
        self.set_status(status)

    # ── PTT 录音 ──

    def _do_recording_blocking(self) -> None:
        if not self.recorder or not self.engine or not self.engine.is_loaded:
            self.set_status("error")
            return
        self.set_status("recording")
        result = self.recorder.record()
        if result is None or result.duration < 0.2:
            self.set_status("idle")
            return
        self.set_status("transcribing")
        audio = result.audio
        quality = None
        if self.config.get("audio_preprocess", True):
            try:
                from audio_quality import preprocess_audio
                audio, quality = preprocess_audio(result.audio, result.sample_rate)
                if quality.warnings:
                    print(f"[app] Audio quality warnings: {', '.join(quality.warnings)}", flush=True)
                print(
                    "[app] Audio prepared: "
                    f"{quality.duration_before:.2f}s -> {quality.duration_after:.2f}s, "
                    f"rms {quality.rms_before:.4f} -> {quality.rms_after:.4f}",
                    flush=True,
                )
            except Exception as e:
                print(f"[app] Audio preprocessing skipped: {e}", flush=True)
                audio = result.audio

        text = self.engine.transcribe(audio, result.sample_rate)
        if text:
            # 自动添加标点符号
            if self.config.get("punctuation_enabled", True) and self.punctuation and self.punctuation.is_loaded:
                try:
                    text = self.punctuation.add_punctuation(text)
                except Exception as e:
                    print(f"[app] Punctuation failed: {e}", flush=True)

            try:
                from postprocess import apply_postprocess
                text = apply_postprocess(
                    text,
                    replacements=self.config.get("text_replacements", {}),
                )
            except Exception as e:
                print(f"[app] Text postprocess skipped: {e}", flush=True)

            if self.config.get("save_audio_samples", False) and quality is not None:
                try:
                    from audio_quality import save_audio_sample
                    path = save_audio_sample(
                        audio,
                        result.sample_rate,
                        text,
                        quality,
                        keep=int(self.config.get("sample_keep", 10)),
                    )
                    print(f"[app] Saved audio sample: {path}", flush=True)
                except Exception as e:
                    print(f"[app] Audio sample save skipped: {e}", flush=True)

            print(f"[app] Transcribed: {text[:60]}", flush=True)
            from clipboard import copy_and_paste
            ok = copy_and_paste(text, auto_paste=self.config.get("auto_paste", True))
            if not ok:
                print("[app] Paste failed", flush=True)
        else:
            print("[app] No text recognized", flush=True)
        self.set_status("idle")

    def start_recording(self) -> None:
        if self._status in ("recording", "transcribing"):
            return
        if not self.engine or not self.engine.is_loaded:
            self._pending_recording = True
            return
        self._record_thread = threading.Thread(
            target=self._do_recording_blocking, daemon=True
        )
        self._record_thread.start()

    def stop_recording(self) -> None:
        if self.recorder:
            self.recorder.stop()
        self._pending_recording = False

    # ── pynput 热键 ──

    def _start_hotkey_listener(self):
        from pynput import keyboard as kb

        ptt_key_str = self.config.get("hotkey", "ctrl_r")
        ptt_key = getattr(kb.Key, ptt_key_str, None)
        if ptt_key is None:
            print(f"[app] Invalid PTT key: {ptt_key_str}", flush=True)
            return

        print(f"[app] PTT: hold [{ptt_key_str}] to talk", flush=True)

        def on_press(key):
            try:
                if key == ptt_key:
                    self.start_recording()
            except Exception:
                pass

        def on_release(key):
            try:
                if key == ptt_key:
                    self.stop_recording()
            except Exception:
                pass

        with kb.Listener(on_press=on_press, on_release=on_release) as listener:
            listener.join()

    # ── 设置窗口 ──

    def open_settings(self) -> None:
        from settings import SettingsWindow

        try:
            win = SettingsWindow(self.config)
            win.config_saved.connect(self._on_config_saved)
            win.exec()
            print("[app] Settings closed", flush=True)
        except Exception as e:
            import traceback
            print(f"[app] Settings ERROR: {e}", flush=True)
            traceback.print_exc()

    def _on_config_saved(self, new_config: dict) -> None:
        from config import save_config
        from recorder import VoiceRecorder

        self.config = new_config
        save_config(self.config)
        self.recorder = VoiceRecorder(
            device=self.config.get("device"),
            on_status_change=self._on_recorder_status,
        )

    def _update_loading_animation(self):
        colors = ["#6b7280", "#4ade80", "#6b7280", "#22c55e"]
        self._loading_anim_frame = (self._loading_anim_frame + 1) % len(colors)
        pix = _make_pixmap(colors[self._loading_anim_frame])
        if self.tray:
            self.tray.setIcon(QIcon(pix))

    def _on_exit(self) -> None:
        if self._loading_anim_timer:
            self._loading_anim_timer.stop()
        if self.engine:
            self.engine.unload()
        if self.punctuation:
            self.punctuation.unload()
        QApplication.quit()

    # ── 启动 ──

    def run(self) -> None:
        print("[Voice Input] Starting...", flush=True)

        from recorder import VoiceRecorder
        from engine import ASREngine

        self.recorder = VoiceRecorder(
            device=self.config.get("device"),
            on_status_change=self._on_recorder_status,
        )

        self.engine = ASREngine(
            model_name=self.config.get("model", "small"),
            on_status_change=self._on_engine_status,
        )

        # 标点模型（独立于 ASR 引擎）
        self.punctuation = None
        if self.config.get("punctuation_enabled", True):
            from punctuation import PunctuationProcessor
            self.punctuation = PunctuationProcessor(
                model_name=self.config.get("punctuation_model", ""),
            )

        # 所有 Qt 界面延迟到事件循环启动后创建
        def _init_ui():
            self.tray = QSystemTrayIcon(_get_icons()["idle"], self.app)
            self.tray.setToolTip("Voice Input — 按住 PTT 键说话")
            menu = QMenu()
            menu.addAction("录音 (按住 PTT 键)", self.start_recording)
            menu.addAction("设置", self.open_settings)
            menu.addSeparator()
            menu.addAction("退出", self._on_exit)
            self.tray.setContextMenu(menu)
            self.tray.setToolTip("Voice Input — 正在加载模型…")
            self.tray.show()

            # 加载动画
            self._loading_anim_timer = QTimer(self.app)
            self._loading_anim_timer.timeout.connect(self._update_loading_animation)
            self._loading_anim_timer.start(500)

        QTimer.singleShot(0, _init_ui)

        def _load():
            self.engine.load()
            # 标点模型延迟加载（不阻塞 ASR）
            if self.punctuation:
                try:
                    self.punctuation.load()
                except Exception as e:
                    print(f"[app] Punctuation model load failed: {e}", flush=True)

        threading.Thread(target=_load, daemon=True).start()

        # PTT 热键监听 (独立线程)
        threading.Thread(target=self._start_hotkey_listener, daemon=True).start()

        print("[Voice Input] Starting UI + model...", flush=True)


if __name__ == "__main__":
    # 输出重定向到持久化日志文件（pythonw 模式下无控制台）
    from config import CONFIG_DIR
    log_path = CONFIG_DIR / "app.log"
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_file = open(log_path, "w", encoding="utf-8")
        sys.stdout = log_file
        sys.stderr = log_file
    except Exception:
        pass

    print(f"[app] Started at {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print(f"[app] Python: {sys.executable}", flush=True)
    print(f"[app] CWD: {os.getcwd()}", flush=True)

    # 单实例互斥锁
    mutex = win32event.CreateMutex(None, False, "VoiceInput_Mutex")
    if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
        print("[app] Already running, exiting", flush=True)
        sys.exit(0)

    try:
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)
        v = VoiceInputApp()
        v.app = app
        v.run()
        sys.exit(app.exec())
    except Exception as e:
        import traceback
        print(f"[app] FATAL: {e}", flush=True)
        traceback.print_exc(file=log_file if 'log_file' in dir() else sys.stderr)
        raise
