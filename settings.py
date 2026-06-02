"""设置窗口 — PySide6 (模态对话框)"""

from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QCheckBox, QLineEdit,
    QPushButton, QGroupBox, QFormLayout, QMessageBox,
)
from PySide6.QtCore import Qt, Signal

from config import load_config, save_config
from recorder import VoiceRecorder
import autostart


PTT_OPTIONS = [
    ("ctrl_r", "右 Ctrl (推荐)"),
    ("ctrl_l", "左 Ctrl"),
    ("shift_r", "右 Shift"),
    ("shift_l", "左 Shift"),
    ("alt_r", "右 Alt"),
    ("alt_l", "左 Alt"),
    ("caps_lock", "Caps Lock"),
    ("pause", "Pause/Break"),
    ("scroll_lock", "Scroll Lock"),
    ("insert", "Insert"),
    ("f1", "F1"), ("f2", "F2"), ("f3", "F3"), ("f4", "F4"),
    ("f5", "F5"), ("f6", "F6"), ("f7", "F7"), ("f8", "F8"),
    ("f9", "F9"), ("f10", "F10"), ("f11", "F11"), ("f12", "F12"),
    ("__custom__", "自定义..."),
]

CUSTOM_INDEX = len(PTT_OPTIONS) - 1


class SettingsWindow(QDialog):
    """设置对话框 — exec() 模态，确保强制置顶显示"""

    config_saved = Signal(dict)

    def __init__(self, config: Optional[dict] = None):
        super().__init__()
        self.config = config or load_config()
        self.recorder = VoiceRecorder()
        self._init_ui()

    def _init_ui(self) -> None:
        self.setWindowTitle("Voice Input 设置")
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint)
        self.setModal(True)
        self.setMinimumWidth(440)
        self.setFixedHeight(440)

        layout = QVBoxLayout()
        layout.setSpacing(12)

        # ── PTT 热键 ──
        hotkey_group = QGroupBox("按住说话 (PTT)")
        hotkey_layout = QFormLayout()

        self.hotkey_combo = QComboBox()
        for val, label in PTT_OPTIONS:
            self.hotkey_combo.addItem(label, val)

        saved = self.config.get("hotkey", "ctrl_r")
        found = False
        for i in range(self.hotkey_combo.count()):
            if self.hotkey_combo.itemData(i) == saved:
                self.hotkey_combo.setCurrentIndex(i)
                found = True
                break
        if not found:
            self.hotkey_combo.setCurrentIndex(CUSTOM_INDEX)
            self._custom_key_name = saved

        self.hotkey_combo.currentIndexChanged.connect(self._on_hotkey_changed)
        hotkey_layout.addRow("热键:", self.hotkey_combo)

        self.custom_key_input = QLineEdit()
        self.custom_key_input.setPlaceholderText("如 ctrl_r, f13, home, space")
        self.custom_key_input.setVisible(found is False)
        if not found:
            self.custom_key_input.setText(saved)
        hotkey_layout.addRow("", self.custom_key_input)

        hint = QLabel("按住此键开始录音，松开自动识别并粘贴")
        hint.setStyleSheet("color: #888; font-size: 11px;")
        hint.setWordWrap(True)
        hotkey_layout.addRow("", hint)

        hotkey_group.setLayout(hotkey_layout)
        layout.addWidget(hotkey_group)

        # ── 输入设备 ──
        device_group = QGroupBox("麦克风")
        device_layout = QFormLayout()
        self.device_combo = QComboBox()
        self._populate_devices()
        device_layout.addRow("输入设备:", self.device_combo)
        device_group.setLayout(device_layout)
        layout.addWidget(device_group)

        # ── 输出 ──
        output_group = QGroupBox("输出")
        output_layout = QFormLayout()
        self.auto_paste_check = QCheckBox("自动粘贴到当前光标位置")
        self.auto_paste_check.setChecked(self.config.get("auto_paste", True))
        output_layout.addRow(self.auto_paste_check)

        self.auto_start_check = QCheckBox("开机自动启动")
        self.auto_start_check.setChecked(self.config.get("auto_start", False))
        output_layout.addRow(self.auto_start_check)

        self.punct_check = QCheckBox("自动添加标点符号（中英文）")
        self.punct_check.setChecked(self.config.get("punctuation_enabled", True))
        output_layout.addRow(self.punct_check)

        output_group.setLayout(output_layout)
        layout.addWidget(output_group)

        # ── 按钮 ──
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self._on_save)
        self.save_btn.setStyleSheet("""
            QPushButton { background-color: #22c55e; color: white; padding: 8px 20px;
                border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #16a34a; }
        """)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def _on_hotkey_changed(self, idx: int):
        self.custom_key_input.setVisible(idx == CUSTOM_INDEX)

    def _populate_devices(self) -> None:
        self.device_combo.clear()
        self.device_combo.addItem("系统默认", None)
        try:
            for dev in self.recorder.list_devices():
                self.device_combo.addItem(f"[{dev['index']}] {dev['name']}", dev["index"])
            saved = self.config.get("device")
            if saved is not None:
                for i in range(self.device_combo.count()):
                    if self.device_combo.itemData(i) == saved:
                        self.device_combo.setCurrentIndex(i)
                        break
        except Exception as e:
            self.device_combo.addItem(f"获取设备失败: {e}", None)

    def _on_save(self) -> None:
        idx = self.hotkey_combo.currentIndex()
        if idx == CUSTOM_INDEX:
            hotkey = self.custom_key_input.text().strip()
            if not hotkey:
                QMessageBox.warning(self, "错误", "请输入自定义键名")
                return
        else:
            hotkey = self.hotkey_combo.currentData()

        self.config["hotkey"] = hotkey
        self.config["device"] = self.device_combo.currentData()
        self.config["auto_paste"] = self.auto_paste_check.isChecked()
        self.config["punctuation_enabled"] = self.punct_check.isChecked()

        auto_start = self.auto_start_check.isChecked()
        self.config["auto_start"] = auto_start
        if auto_start:
            autostart.enable()
        else:
            autostart.disable()

        save_config(self.config)
        self.config_saved.emit(self.config)
        self.accept()
