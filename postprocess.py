"""Fast text cleanup after ASR."""

from __future__ import annotations

import re


DEFAULT_REPLACEMENTS = {
    "open ai": "OpenAI",
    "openai": "OpenAI",
    "chat gpt": "ChatGPT",
    "chatgpt": "ChatGPT",
    "github": "GitHub",
    "git hub": "GitHub",
    "python": "Python",
}


def _normalize_spaces(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s+([,.;:!?，。！？；：])", r"\1", text)
    return text.strip()


def apply_postprocess(text: str, replacements: dict[str, str] | None = None) -> str:
    """Apply deterministic, low-latency corrections."""
    if not text:
        return text

    cleaned = _normalize_spaces(text)
    merged = dict(DEFAULT_REPLACEMENTS)
    if replacements:
        merged.update({str(k): str(v) for k, v in replacements.items() if str(k)})

    for src, dst in sorted(merged.items(), key=lambda item: len(item[0]), reverse=True):
        cleaned = re.sub(re.escape(src), dst, cleaned, flags=re.IGNORECASE)

    return _normalize_spaces(cleaned)
