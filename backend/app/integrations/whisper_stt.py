"""Primary speech-to-text via faster-whisper (PLAN §8, §15).

Handles all four languages in one local model. Imported lazily so the app boots even
when faster-whisper isn't installed. Requires ffmpeg on PATH for OGG/Opus decoding.
"""
from __future__ import annotations

import asyncio

from app.core.config import settings

_model = None


def _load_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel  # lazy import

        _model = WhisperModel(settings.WHISPER_MODEL, device="cpu", compute_type="int8")
    return _model


def _transcribe_sync(audio_path: str) -> str:
    model = _load_model()
    segments, _info = model.transcribe(audio_path, beam_size=1)
    return " ".join(seg.text for seg in segments).strip()


async def transcribe(audio_path: str) -> str:
    """Transcribe an audio file to text. Returns "" on failure (missing dep / ffmpeg)."""
    try:
        return await asyncio.to_thread(_transcribe_sync, audio_path)
    except Exception:
        return ""
