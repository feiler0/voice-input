"""录音模块 — sounddevice 录音 (PTT: push-to-talk 模式)"""

import time
import threading
import sounddevice as sd
import numpy as np
from dataclasses import dataclass
from typing import Optional, Callable


SAMPLE_RATE = 16000
FRAME_DURATION_MS = 30
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)


@dataclass
class RecordingResult:
    """录音结果"""
    audio: np.ndarray
    duration: float
    sample_rate: int = SAMPLE_RATE


class VoiceRecorder:
    """PTT 模式录音器 — 调用 record() 开始，stop() 结束"""

    def __init__(
        self,
        device: Optional[int] = None,
        on_status_change: Optional[Callable[[str], None]] = None,
    ):
        self.device = device
        self.on_status_change = on_status_change
        self._stop_event = threading.Event()
        self._stream: Optional[sd.InputStream] = None

    def _set_status(self, status: str) -> None:
        if self.on_status_change:
            self.on_status_change(status)

    def list_devices(self) -> list[dict]:
        devices = sd.query_devices()
        inputs = []
        for i, dev in enumerate(devices):
            if dev["max_input_channels"] > 0:
                inputs.append({
                    "index": i,
                    "name": dev["name"],
                    "channels": dev["max_input_channels"],
                    "sample_rate": dev["default_samplerate"],
                })
        return inputs

    def record(self) -> RecordingResult:
        """开始录音，阻塞直到 stop() 被调用
        
        Returns:
            RecordingResult
        """
        self._stop_event.clear()
        self._set_status("recording")

        chunks: list[np.ndarray] = []

        def callback(indata, frames, _time, status):
            if status:
                print(f"[recorder] status: {status}")
            mono = indata[:, 0] if indata.ndim > 1 else indata
            chunks.append(mono.copy())

        try:
            with sd.InputStream(
                device=self.device,
                samplerate=SAMPLE_RATE,
                channels=1,
                blocksize=FRAME_SIZE,
                dtype="float32",
                callback=callback,
            ) as stream:
                self._stream = stream
                # 等待 stop 信号
                self._stop_event.wait()
        finally:
            self._stream = None

        if not chunks:
            return RecordingResult(audio=np.array([], dtype=np.float32), duration=0)

        full = np.concatenate(chunks)
        dur = len(full) / SAMPLE_RATE
        self._set_status("done")
        return RecordingResult(audio=full, duration=dur)

    def stop(self) -> None:
        """停止录音"""
        self._stop_event.set()
