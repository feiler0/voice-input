# 🎤 Voice Input

**录音转文字桌面工具** — 按住热键说话，松开自动转写并粘贴到光标位置。

基于 [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) + SenseVoice 语音识别引擎，支持中英文混合输入。

## 功能

- 🎙️ **PTT 推讲模式** — 按住热键录音，松开自动转写，和微信语音一样直觉
- ⚡ **离线极速转写** — SenseVoice int8 量化模型，延迟 < 0.2s
- 📝 **自动标点** — CT-Transformer 模型自动添加中英文标点符号
- 🔊 **音频预处理** — 自动降噪、增益、掐头去尾，提升嘈杂环境识别率
- 📋 **自动粘贴** — 转写结果直接送到光标位置
- 🟢 **系统托盘** — 图标颜色指示状态（绿=就绪 / 红=录音中 / 黄=转写中）
- 🚀 **开机自启** — 设置里一键开启
- ⚙️ **设置窗口** — 选麦克风、改热键、开关标点

## 安装

### 1. 安装依赖

```bash
cd voice-input
pip install -r requirements.txt
```

### 2. 运行

```bash
python main.py
```

> 首次运行会自动下载 ASR 模型（~229 MB）和标点模型（~160 MB），请保证网络畅通。

## 使用

| 操作 | 效果 |
|------|------|
| 按住 `右 Ctrl` | 开始录音 |
| 松开 `右 Ctrl` | 停止录音 → 转写 → 粘贴 |
| 托盘右键 → 设置 | 打开设置窗口 |
| 托盘右键 → 退出 | 退出程序 |

### 设置项

| 设置 | 说明 |
|------|------|
| 热键 | 按键说话键（默认右 Ctrl） |
| 输入设备 | 选择麦克风（默认系统默认） |
| 自动粘贴 | 转写完成后自动粘贴到光标位置 |
| 开机自动启动 | 登录系统时自动运行 |
| 自动添加标点符号 | 中英文标点恢复 |

## 项目结构

```
voice-input/
├── main.py            # 入口：托盘 + PTT 热键 + 工作流编排
├── recorder.py        # sounddevice 录音模块
├── engine.py          # SenseVoice ASR 引擎封装
├── punctuation.py     # 标点符号恢复（CT-Transformer）
├── audio_quality.py   # 音频预处理（降噪/增益/掐头去尾）
├── postprocess.py     # 转写文本后处理（去空格/词语替换）
├── clipboard.py       # 剪贴板 + 模拟粘贴
├── settings.py        # PySide6 设置窗口
├── config.py          # 配置管理
├── autostart.py       # Windows 开机自启
├── diagnose.py        # 诊断工具
├── build.bat          # PyInstaller 打包脚本
├── voice-input.spec   # PyInstaller 配置文件
└── requirements.txt
```

## 打包成 exe

```bash
pip install pyinstaller
pyinstaller voice-input.spec
```

## 许可

MIT
