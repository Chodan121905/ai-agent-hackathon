"""Sponsor STT path via VideoDB (PLAN §8).

Note: VideoDB lacks Malay/Tamil, so Whisper is primary; this stays for EN/ZH and future
video search. Lazily imported so a missing package never blocks boot.
"""
from __future__ import annotations

import asyncio

from app.core.config import settings


def _transcribe_sync(audio_path: str) -> str:
    import videodb  # lazy import

    conn = videodb.connect(api_key=settings.VIDEO_DB_API_KEY)
    audio = conn.upload(file_path=audio_path)
    audio.generate_transcript()
    return (audio.get_transcript_text() or "").strip()


async def transcribe(audio_path: str) -> str:
    if not settings.VIDEO_DB_API_KEY:
        return ""
    try:
        return await asyncio.to_thread(_transcribe_sync, audio_path)
    except Exception:
        return ""
