"""Phase 3 — extract. One branch runs per invocation (image | voice | link | text).

Each turns its input into text/intel that downstream phases (intent, analyze, verify,
synthesize) can use. Voice is transcribed here so a spoken command like "use English"
is understood too.
"""
from __future__ import annotations

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
    text = ""
    if settings.STT_PROVIDER == "videodb":
        text = await videodb_stt.transcribe(path)
    if not text:
        text = await whisper_stt.transcribe(path)
    if not text:
        return {}
    # the transcript IS the message — feed it as raw_text so intent + synthesize see it
    return {"raw_text": text}


async def link_intel(state: dict) -> dict:
    intel: list[dict] = []
    for url in (state.get("urls") or [])[:5]:
        intel.append(
            {
                "url": url,
                "domain_intel": await brightdata.domain_intel(url),
                "sandbox": await daytona.safe_open(url),
            }
        )
    return {"link_intel": intel}
