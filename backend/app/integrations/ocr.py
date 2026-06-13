"""Screenshot OCR via TokenRouter (OpenAI-compatible vision), with a Kimi-vision fallback.

When a member forwards a photo (fake bank login, phishing chat, an SMS picture), this
extracts the text so the agent can analyze it. Primary backend is a vision model on
TokenRouter (OCR_MODEL); if TokenRouter isn't configured, it falls back to the main
LLM's vision (Kimi k2.6). Returns "" if no vision backend is available.
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
    # primary: TokenRouter vision model
    if settings.TOKENROUTER_API_KEY and settings.OCR_MODEL:
        try:
            return await _vision_ocr(
                settings.TOKENROUTER_BASE_URL,
                settings.TOKENROUTER_API_KEY,
                settings.OCR_MODEL,
                image_bytes,
            )
        except Exception:
            pass  # fall through to Kimi-vision

    # fallback: the main LLM's vision (Kimi k2.6)
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
