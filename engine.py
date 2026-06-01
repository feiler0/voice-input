"""ASR 引擎 — sherpa-onnx + SenseVoice 封装

相比 whisper.cpp:
- SenseVoice 中文识别准确率显著更高
- 支持中/英/日/韩/粤语自动检测
- int8 量化模型 ~229 MB，内存占用 ~500 MB
- 无需 torch，纯 ONNX 推理

注意: sherpa-onnx Windows C++ 层不支持含非 ASCII 字符的路径，
模型会在首次加载时自动缓存到 ASCII-only 的目录。
"""

import os
import sys
import time
import shutil
import numpy as np
from typing import Optional, Callable
import sherpa_onnx


def _get_cache_dir() -> str:
    """返回纯 ASCII 的模型缓存目录"""
    if os.name == "nt":
        base = os.environ.get("APPDATA", os.path.join(os.path.expanduser("~"), "AppData", "Roaming"))
    else:
        base = os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "voice-input", "models")


def _ensure_ascii_path(model_dir: str) -> str:
    """确保模型路径不含非 ASCII 字符，否则复制到缓存目录"""
    try:
        model_dir.encode("ascii")
        return model_dir
    except (UnicodeEncodeError, UnicodeDecodeError):
        cache_dir = _get_cache_dir()
        dst = os.path.join(cache_dir, os.path.basename(model_dir))
        if not os.path.exists(dst):
            os.makedirs(cache_dir, exist_ok=True)
            shutil.copytree(model_dir, dst)
        return dst


class ASREngine:
    """sherpa-onnx SenseVoice 引擎封装"""

    def __init__(
        self,
        model_name: str = "",
        on_status_change: Optional[Callable[[str], None]] = None,
        device: str = "cpu",
    ):
        """
        Args:
            model_name: 模型目录路径，为空则自动使用 models/ 下的默认模型
            on_status_change: 状态回调
            device: 运行设备 (cpu/cuda), 默认 cpu
        """
        self.model_name = model_name
        self.on_status_change = on_status_change
        self._recognizer: Optional[sherpa_onnx.OfflineRecognizer] = None
        self._provider = "cpu" if device == "cpu" else "cuda"

    def _set_status(self, status: str) -> None:
        if self.on_status_change:
            self.on_status_change(status)

    def _log(self, msg: str):
        print(msg, flush=True)
        try:
            from config import CONFIG_DIR
            path = CONFIG_DIR / "engine.log"
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")
        except Exception:
            pass

    def _resolve_model_paths(self) -> tuple[str, str]:
        """返回 (model_path, tokens_path)，确保路径为纯 ASCII"""
        if self.model_name and os.path.isdir(self.model_name):
            model_dir = self.model_name
        else:
            # PyInstaller 打包后: 模型在 exe 同级的 models/ 目录
            if getattr(sys, "frozen", False):
                base_dir = os.path.join(os.path.dirname(sys.executable), "models")
            else:
                base_dir = os.path.join(os.path.dirname(__file__), "models")
            model_dir = os.path.join(
                base_dir, "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17"
            )

        # sherpa-onnx C++ 不支持非 ASCII 路径 → 缓存到 ASCII-only 目录
        model_dir = _ensure_ascii_path(model_dir)

        model_path = os.path.join(model_dir, "model.int8.onnx")
        tokens_path = os.path.join(model_dir, "tokens.txt")

        # Fallback to fp32 if int8 not found
        if not os.path.exists(model_path):
            model_path = os.path.join(model_dir, "model.onnx")

        return model_path, tokens_path

    def load(self) -> bool:
        """加载模型"""
        self._set_status("loading_model")
        try:
            t0 = time.time()

            model_path, tokens_path = self._resolve_model_paths()

            if not os.path.exists(model_path):
                self._log(f"Model not found at {model_path}")
                self._set_status("error")
                return False

            self._log(f"Loading SenseVoice model: {model_path}")

            self._recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
                model=model_path,
                tokens=tokens_path,
                num_threads=4,
                use_itn=False,
                language="zh",
                debug=False,
                provider=self._provider,
            )

            elapsed = time.time() - t0
            self._log(f"Model loaded in {elapsed:.1f}s")
            self._set_status("ready")
            return True

        except Exception as e:
            self._log(f"Failed to load model: {e}")
            import traceback
            traceback.print_exc()
            self._set_status("error")
            return False

    @property
    def is_loaded(self) -> bool:
        return self._recognizer is not None

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> Optional[str]:
        """转写音频为文字

        Args:
            audio: float32 numpy 数组, [-1, 1]
            sample_rate: 采样率

        Returns:
            转写文本，失败返回 None
        """
        if self._recognizer is None:
            print("[engine] Model not loaded")
            return None

        try:
            self._set_status("transcribing")

            t0 = time.time()
            stream = self._recognizer.create_stream()
            stream.accept_waveform(sample_rate, audio)
            self._recognizer.decode_stream(stream)
            text = stream.result.text.strip()
            elapsed = time.time() - t0

            if text:
                self._log(f"Transcribed in {elapsed:.2f}s: \"{text[:60]}\"")
                self._set_status("ready")
                return text
            else:
                self._log("Empty result")
                self._set_status("ready")
                return None

        except Exception as e:
            self._log(f"Transcription error: {e}")
            self._set_status("error")
            return None

    def unload(self) -> None:
        """释放模型"""
        self._recognizer = None
        self._set_status("unloaded")
        import gc
        gc.collect()
