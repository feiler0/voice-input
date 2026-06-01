# 🎤 Voice Input

**录音转文字桌面工具** — 按热键说话，文字自动出现在光标位置。

基于阿里达摩院 [SenseVoice](https://github.com/modelscope/FunASR) 语音识别引擎。

## 功能

- 🎙️ **全局热键录音** — 默认 `Ctrl+Shift+R`，按了就说
- 🔇 **VAD 自动停止** — 说完静音 1.5s 自动停止录音
- ⚡ **SenseVoice 快速转写** — 中文准确率高，延迟 < 1s
- 📋 **自动粘贴** — 转出来的文字直接送到当前光标位置
- 🟢 **系统托盘** — 图标颜色指示状态（绿=就绪 / 红=录音中 / 黄=转写中）
- ⚙️ **设置窗口** — 选麦克风、改热键、调静音灵敏度

## 安装

### 1. 安装依赖

```bash
cd voice-input
pip install -r requirements.txt
```

> 首次运行会自动下载 SenseVoice 模型（~600MB），请保证网络畅通。

### 2. 运行

```bash
python main.py
```

托盘图标出现后，按 `Ctrl+Shift+R` 开始说话，说完自动粘贴。

## 使用

| 操作 | 效果 |
|------|------|
| `Ctrl+Shift+R` | 开始/停止录音 |
| 托盘右键 → 设置 | 打开设置窗口 |
| 托盘右键 → 退出 | 退出程序 |

### 设置项

| 设置 | 说明 |
|------|------|
| 输入设备 | 选择麦克风（默认=系统默认） |
| 静音超时 | 说完话后等多久自动停止（默认 1.5s） |
| 全局热键 | 录音快捷键 |
| 自动粘贴 | 勾选后转写完成自动 Ctrl+V |

## 截图

```
[绿] 🟢 就绪 → 按热键 → [红] 🔴 录音中 → 说话 → [黄] 🟡 转写中 → 文字粘贴 ✓
```

## 项目结构

```
voice-input/
├── main.py          # 入口：托盘 + 热键 + 工作流
├── recorder.py      # 录音 + VAD 静音检测
├── engine.py        # SenseVoice ASR 封装
├── clipboard.py     # 剪贴板 + 模拟粘贴
├── settings.py      # PySide6 设置窗口
├── config.py        # 配置管理
└── requirements.txt
```

## 打包成 exe

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --add-data "path/to/sensevoice;." main.py
```

## 许可

MIT
