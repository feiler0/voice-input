"""标点符号恢复 — sherpa-onnx OfflinePunctuation 封装

使用 CT-Transformer 模型，支持中英文混合文本。
模型约 160 MB (int8 量化)，首次使用自动下载。
"""

import os
import sys
import time
import urllib.request
import tarfile
from typing import Optional

import sherpa_onnx


# 默认标点模型目录名
DEFAULT_PUNCT_MODEL = "sherpa-onnx-punct-ct-transformer-zh-en-vocab272727-2024-04-12-int8"
MODEL_URL = (
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/punctuation-models/"
    "sherpa-onnx-punct-ct-transformer-zh-en-vocab272727-2024-04-12-int8.tar.bz2"
)


def _get_models_dir() -> str:
    """返回 models 目录路径"""
    if getattr(sys, "frozen", False):
        return os.path.join(os.path.dirname(sys.executable), "models")
    else:
        return os.path.join(os.path.dirname(__file__), "models")


def _resolve_punct_model_path(model_name: str = "") -> str:
    """返回标点模型的 ONNX 文件路径"""
    if model_name and os.path.isdir(model_name):
        model_dir = model_name
    elif model_name and os.path.isfile(model_name):
        return model_name
    else:
        model_dir = os.path.join(_get_models_dir(), DEFAULT_PUNCT_MODEL)

    # 优先 int8 量化模型
    int8_path = os.path.join(model_dir, "model.int8.onnx")
    if os.path.exists(int8_path):
        return int8_path
    return os.path.join(model_dir, "model.onnx")


def download_model() -> bool:
    """下载标点模型到 models 目录（约 160 MB）"""
    models_dir = _get_models_dir()
    model_dir = os.path.join(models_dir, DEFAULT_PUNCT_MODEL)

    if os.path.exists(os.path.join(model_dir, "model.int8.onnx")) or \
       os.path.exists(os.path.join(model_dir, "model.onnx")):
        print("[punct] Model already exists", flush=True)
        return True

    archive_path = os.path.join(models_dir, "punct-model.tar.bz2")

    try:
        os.makedirs(models_dir, exist_ok=True)

        print(f"[punct] Downloading model (~160 MB)...", flush=True)
        urllib.request.urlretrieve(MODEL_URL, archive_path)

        print("[punct] Extracting...", flush=True)
        with tarfile.open(archive_path, "r:bz2") as tar:
            tar.extractall(models_dir)

        os.remove(archive_path)
        print("[punct] Model downloaded successfully", flush=True)
        return True
    except Exception as e:
        print(f"[punct] Download failed: {e}", flush=True)
        if os.path.exists(archive_path):
            try:
                os.remove(archive_path)
            except Exception:
                pass
        return False


class PunctuationProcessor:
    """标点符号恢复处理器"""

    def __init__(self, model_name: str = ""):
        self._model_name = model_name
        self._punct: Optional[sherpa_onnx.OfflinePunctuation] = None

    def load(self) -> bool:
        """加载标点模型，如本地不存在则自动下载"""
        try:
            model_path = _resolve_punct_model_path(self._model_name)

            if not os.path.exists(model_path):
                print(f"[punct] Model not found, downloading...", flush=True)
                if not download_model():
                    print("[punct] Auto-download failed. "
                          "Download manually from "
                          "https://github.com/k2-fsa/sherpa-onnx/releases/tag/punctuation-models "
                          f"and extract to {_get_models_dir()}", flush=True)
                    return False
                model_path = _resolve_punct_model_path(self._model_name)
                if not os.path.exists(model_path):
                    return False

            t0 = time.time()
            config = sherpa_onnx.OfflinePunctuationConfig(
                model=sherpa_onnx.OfflinePunctuationModelConfig(
                    ct_transformer=model_path,
                ),
            )
            self._punct = sherpa_onnx.OfflinePunctuation(config)
            print(f"[punct] Model loaded in {time.time() - t0:.1f}s", flush=True)
            return True
        except Exception as e:
            print(f"[punct] Failed to load model: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return False

    @property
    def is_loaded(self) -> bool:
        return self._punct is not None

    def add_punctuation(self, text: str) -> str:
        """给文本添加标点符号"""
        if not text or not self._punct:
            return text
        try:
            result = self._punct.add_punctuation(text)
            return result if result else text
        except Exception as e:
            print(f"[punct] Error: {e}", flush=True)
            return text

    def unload(self) -> None:
        self._punct = None
