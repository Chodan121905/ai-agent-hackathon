"""Phase 3 — extract. One branch runs per invocation (image | voice | link | text).

Each turns its input into text/intel that downstream phases (intent, analyze, verify,
synthesize) can use. Voice is transcribed here so a spoken command like "use English"
is understood too.
"""
from __future__ import annotations

import asyncio

from app.agent.nodes.intake import route_by_modality  # re-export for graph wiring
from app.agent.util import find_urls
from app.core.config import settings
from app.integrations import brightdata, daytona, ocr as ocr_client, videodb_stt, whisper_stt

__all__ = ["route_by_modality", "ocr", "transcribe", "link_intel"]


async def ocr(state: dict) -> dict:
    img = state.get("image_bytes")
    if not img:
        return {}
    text = await ocr_client.ocr(img)
    if not text:
        return {}
    updates: dict = {"extracted_text": [text]}
    # surface any URLs the screenshot contained so they can be checked downstream
    found = find_urls(text)
    if found:
        updates["urls"] = list({*(state.get("urls") or []), *found})
    return updates


async def transcribe(state: dict) -> dict:
    path = state.get("audio_path")
    if not path:
        return {}
    # Use ONLY the configured provider — no cross-fallback. (faster-whisper/ctranslate2
    # segfaults on CPUs without the required instruction set, which would crash the whole
    # process, so we never call it unless it is explicitly selected.)
    if settings.STT_PROVIDER == "whisper":
        text = await whisper_stt.transcribe(path)
    else:
        text = await videodb_stt.transcribe(path)
    if not text:
        # couldn't understand the audio (or no STT installed) — flag it so we don't run a
        # scam check on empty content and return a bogus "nothing to review" verdict
        return {"audio_failed": True}
    # the transcript IS the message — feed it as raw_text so intent + synthesize see it
    return {"raw_text": text}


async def link_intel(state: dict) -> dict:
    urls = (state.get("urls") or [])[:3]
    if not urls:
        return {}

    async def one(url: str) -> dict:
        # Bright Data domain intel and the Daytona sandbox run concurrently per URL.
        domain_intel, sandbox = await asyncio.gather(
            brightdata.domain_intel(url), daytona.safe_open(url)
        )
        return {"url": url, "domain_intel": domain_intel, "sandbox": sandbox}

    intel = await asyncio.gather(*[one(u) for u in urls])
    return {"link_intel": list(intel)}
