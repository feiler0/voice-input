# Voice Input Tool — Design Spec

**Date:** 2026-05-26
**Status:** approved

## Overview

A lightweight Windows system tray tool that provides push-to-talk voice input. User holds a customizable hotkey, speaks, releases the hotkey — speech is transcribed to text and pasted at the current cursor position.

Target use case: voice input for the Claude Code input box in VSCode, but works universally in any text field.

## Interaction Flow

```
Hold hotkey (Ctrl+Alt+V default, customizable)
  → tray icon turns green (recording)
  → audio captured from default microphone
Release hotkey
  → tray icon turns yellow (transcribing)
  → Windows built-in Speech API transcribes to Chinese text
  → tray icon flashes back to normal (standby)
  → text pasted at cursor via clipboard + Ctrl+V
```

Edge cases:
- Recording over 60s auto-stops (prevents runaway recording if key gets stuck)
- Empty transcription (no speech detected) → no paste, silent no-op
- Microphone unavailable → tray icon shows error state briefly

## Architecture

```
VoiceInput/
├── main.py             # Entry point: tray icon lifecycle, hotkey registration
├── recorder.py          # AudioRecorder: start()/stop(), returns WAV bytes
├── recognizer.py        # SpeechRecognizer: transcribe(wav_bytes) → str
├── settings.json        # Customizable hotkey, language
└── requirements.txt     # pyaudio, SpeechRecognition, pystray, Pillow,
                         #   pynput, pyperclip, keyboard
```

### main.py
- Creates system tray icon with 3 states (standby/recording/transcribing)
- Registers global hotkey via `keyboard` or `pynput` (using settings.json)
- Hotkey press → `recorder.start()` → icon green
- Hotkey release → `recorder.stop()` → icon yellow → `recognizer.transcribe()` → `Ctrl+V` paste → icon normal
- Right-click tray menu: Settings, Exit
- Left-click tray: toggle hotkey on/off

### recorder.py
- `AudioRecorder` class
- `start()`: opens PyAudio stream, begins capturing to in-memory buffer
- `stop()`: closes stream, returns WAV bytes (16kHz mono 16-bit)
- Timeout: auto-stop after 60s
- Error: raises `DeviceNotFound` or returns empty bytes if mic unavailable

### recognizer.py
- `SpeechRecognizer` class
- `transcribe(wav_bytes) → str`
- Uses `speech_recognition` library with `recognize_sphinx` or Windows Speech API
- Configurable language (default zh-CN)
- Returns empty string if nothing recognized

### settings.json
```json
{
  "hotkey": "ctrl+alt+v",
  "language": "zh-CN",
  "max_record_seconds": 60
}
```

## Dependencies

| Library | Purpose |
|---------|---------|
| `pyaudio` | Microphone audio capture |
| `SpeechRecognition` | Speech-to-text (Windows Speech API backend) |
| `pystray` | System tray icon |
| `Pillow` | Tray icon image generation |
| `pynput` | Global hotkey monitoring + Ctrl+V simulation |
| `pyperclip` | Clipboard text copy |

All libraries available via pip, no system dependencies beyond a working microphone.

## Error Handling

| Scenario | Behavior |
|----------|----------|
| No microphone | Tray icon error state, tooltip shows "Microphone not found" |
| Hotkey conflict | Log warning, allow user to change in settings.json |
| Empty recognition | Silent no-op |
| Recognition timeout | Paste what was recognized so far |
| Recording >60s | Auto-stop and transcribe |
