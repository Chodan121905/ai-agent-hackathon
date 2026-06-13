"""Screenshot OCR via SenseNova U1 (sponsor), with a Kimi-vision fallback (PLAN §8).

Both are OpenAI-compatible vision chat endpoints, so we send the image as a data-URI.
The exact hosted "U1" model id is configurable (SENSENOVA_MODEL); if SenseNova is not
configured or errors, we fall back to the Kimi brain's vision capability.
"""
from __future__ import annotations

import base64

import httpx

from app.core.config import settings

_OCR_INSTRUCTION = (
    "Extract ALL readable text from this image exactly as written, preserving order. "
    "If it is a screenshot of a message, chat, email, or website, include sender names, "
    "addresses, URLs, and button text. Output only the extracted text."
)


def _data_uri(image_bytes: bytes, mime: str = "image/png") -> str:
    return f"data:{mime};base64,{base64.b64encode(image_bytes).decode()}"


async def _vision_ocr(base_url: str, api_key: str, model: str, image_bytes: bytes) -> str:
    payload = {
        "model": model,
        "temperature": 0,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": _OCR_INSTRUCTION},
                    {"type": "image_url", "image_url": {"url": _data_uri(image_bytes)}},
                ],
            }
        ],
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()


async def ocr(image_bytes: bytes) -> str:
    """Read text out of a screenshot. Returns "" if no OCR backend is available."""
    if settings.SENSENOVA_API_KEY:
        try:
            return await _vision_ocr(
                settings.SENSENOVA_BASE_URL,
                settings.SENSENOVA_API_KEY,
                settings.SENSENOVA_MODEL,
                image_bytes,
            )
        except Exception:
            pass  # fall through to Kimi-vision

    if settings.llm_configured:
        try:
            return await _vision_ocr(
                settings.LLM_BASE_URL,
                settings.LLM_API_KEY,
                settings.LLM_MODEL_BRAIN,
                image_bytes,
            )
        except Exception:
            pass

    return ""


async def scam_of_week_card(prompt: str) -> str | None:
    """Optional: SenseNova image generation for the weekly card. Returns a URL or None.

    Image generation API shape is provider-specific and not load-bearing for the demo,
    so this is left as a documented no-op when not configured.
    """
    return None
