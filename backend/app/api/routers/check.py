"""POST /api/v1/check — the core endpoint. Same brain as Telegram + email."""
from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.schemas.check import CheckResponse
from app.services import check_service

router = APIRouter(prefix="/check", tags=["check"])


@router.post("", response_model=CheckResponse, operation_id="check")
async def check(
    text: str | None = Form(default=None),
    url: str | None = Form(default=None),
    image: UploadFile | None = File(default=None),
    audio: UploadFile | None = File(default=None),
    session: AsyncSession = Depends(get_session),
) -> CheckResponse:
    image_bytes = await image.read() if image else None

    audio_path = None
    if audio:
        suffix = Path(audio.filename or "a.ogg").suffix or ".ogg"
        tmp = Path(tempfile.gettempdir()) / f"sg_api_{audio.filename or 'audio'}{suffix}"
        tmp.write_bytes(await audio.read())
        audio_path = str(tmp)

    try:
        result = await check_service.run_check(
            session=session,
            bot=None,  # web channel has no Telegram context → no push alert
            source={"channel": "web"},
            raw_text=text or "",
            image_bytes=image_bytes,
            audio_path=audio_path,
            urls=[url] if url else None,
        )
    finally:
        if audio_path:
            Path(audio_path).unlink(missing_ok=True)

    if result.get("intent") == "set_language":
        return CheckResponse(intent="set_language", message=result.get("message"), languages=result.get("languages"))
    return CheckResponse(
        intent="check",
        verdict=result["verdict"],
        report_id=result.get("report_id"),
        alerted=result.get("alerted", 0),
    )
