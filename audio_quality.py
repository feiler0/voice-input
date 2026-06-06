"""Audio preprocessing and sample capture helpers."""

from __future__ import annotations

import json
import wave
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import numpy as np

from config import CONFIG_DIR


@dataclass
class AudioQuality:
    duration_before: float
    duration_after: float
    rms_before: float
    rms_after: float
    peak_before: float
    peak_after: float
    clipped_ratio: float
    warnings: list[str]


def _rms(audio: np.ndarray) -> float:
    if audio.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(audio, dtype=np.float64))))


def _peak(audio: np.ndarray) -> float:
    if audio.size == 0:
        return 0.0
    return float(np.max(np.abs(audio)))


def _trim_silence(
    audio: np.ndarray,
    sample_rate: int,
    frame_ms: int = 20,
    threshold_ratio: float = 0.12,
    padding_ms: int = 160,
) -> np.ndarray:
    if audio.size == 0:
        return audio

    frame_size = max(1, int(sample_rate * frame_ms / 1000))
    if audio.size <= frame_size:
        return audio

    frames = []
    for start in range(0, audio.size, frame_size):
        frame = audio[start:start + frame_size]
        if frame.size:
            frames.append(_rms(frame))

    if not frames:
        return audio

    frame_rms = np.asarray(frames, dtype=np.float32)
    noise_floor = float(np.percentile(frame_rms, 20))
    speech_level = float(np.percentile(frame_rms, 90))
    threshold = max(noise_floor * 2.5, speech_level * threshold_ratio, 0.003)
    active = np.flatnonzero(frame_rms >= threshold)
    if active.size == 0:
        return audio

    pad = int(sample_rate * padding_ms / 1000)
    start = max(0, int(active[0]) * frame_size - pad)
    end = min(audio.size, (int(active[-1]) + 1) * frame_size + pad)
    return audio[start:end]


def _normalize(audio: np.ndarray, target_rms: float = 0.10, max_gain: float = 8.0) -> np.ndarray:
    if audio.size == 0:
        return audio

    current_rms = _rms(audio)
    if current_rms <= 1e-6:
        return audio

    gain = min(max_gain, target_rms / current_rms)
    normalized = audio * gain
    peak = _peak(normalized)
    if peak > 0.98:
        normalized = normalized * (0.98 / peak)
    return normalized.astype(np.float32)


def _fade_edges(audio: np.ndarray, sample_rate: int, fade_ms: int = 8) -> np.ndarray:
    fade = int(sample_rate * fade_ms / 1000)
    if fade <= 1 or audio.size < fade * 2:
        return audio

    out = audio.copy()
    ramp = np.linspace(0.0, 1.0, fade, dtype=np.float32)
    out[:fade] *= ramp
    out[-fade:] *= ramp[::-1]
    return out


def preprocess_audio(audio: np.ndarray, sample_rate: int) -> tuple[np.ndarray, AudioQuality]:
    """Clean speech audio before ASR without changing the sample rate."""
    if audio is None:
        audio = np.array([], dtype=np.float32)

    raw = np.asarray(audio, dtype=np.float32)
    raw = np.nan_to_num(raw, nan=0.0, posinf=0.0, neginf=0.0)
    raw = np.clip(raw, -1.0, 1.0)

    warnings: list[str] = []
    rms_before = _rms(raw)
    peak_before = _peak(raw)
    clipped_ratio = float(np.mean(np.abs(raw) >= 0.98)) if raw.size else 0.0

    cleaned = raw - float(np.mean(raw)) if raw.size else raw
    cleaned = _trim_silence(cleaned, sample_rate)
    cleaned = _normalize(cleaned)
    cleaned = _fade_edges(cleaned, sample_rate)
    cleaned = np.clip(cleaned, -1.0, 1.0).astype(np.float32)

    rms_after = _rms(cleaned)
    peak_after = _peak(cleaned)
    duration_before = raw.size / sample_rate if sample_rate else 0.0
    duration_after = cleaned.size / sample_rate if sample_rate else 0.0

    if duration_after < 0.35:
        warnings.append("recording_too_short")
    if rms_before < 0.01:
        warnings.append("input_too_quiet")
    if clipped_ratio > 0.01:
        warnings.append("input_clipping")
    if peak_after < 0.02:
        warnings.append("processed_audio_too_quiet")

    quality = AudioQuality(
        duration_before=duration_before,
        duration_after=duration_after,
        rms_before=rms_before,
        rms_after=rms_after,
        peak_before=peak_before,
        peak_after=peak_after,
        clipped_ratio=clipped_ratio,
        warnings=warnings,
    )
    return cleaned, quality


def _to_pcm16(audio: np.ndarray) -> bytes:
    clipped = np.clip(audio, -1.0, 1.0)
    pcm = (clipped * 32767.0).astype("<i2")
    return pcm.tobytes()


def _remove_old_files(paths: Iterable[Path], keep: int) -> None:
    sorted_paths = sorted(paths, key=lambda p: p.stat().st_mtime, reverse=True)
    for path in sorted_paths[keep:]:
        try:
            path.unlink()
        except OSError:
            pass


def save_audio_sample(
    audio: np.ndarray,
    sample_rate: int,
    text: str | None,
    quality: AudioQuality,
    keep: int = 10,
) -> Path:
    """Save a recent processed sample for manual accuracy checks."""
    sample_dir = CONFIG_DIR / "samples"
    sample_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    wav_path = sample_dir / f"{stamp}.wav"
    meta_path = sample_dir / f"{stamp}.json"

    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(_to_pcm16(audio))

    metadata = {
        "text": text or "",
        "quality": asdict(quality),
        "sample_rate": sample_rate,
    }
    meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    _remove_old_files(sample_dir.glob("*.wav"), keep)
    _remove_old_files(sample_dir.glob("*.json"), keep)
    return wav_path
