"""The one brain entry point (PLAN §4). Telegram forwards, the email poller, and the REST
/check endpoint all call this. Runs the agent, persists a report, and (if a bot is given
and the verdict is high enough) fires the family alert."""
from __future__ import annotations

import json

from app.agent.graph import get_graph
from app.agent.verdict import Verdict
from app.models.tables import Report
from app.services import alert_service, member_service


async def run_check(
    *,
    session,
    bot=None,
    source: dict,
    raw_text: str = "",
    image_bytes: bytes | None = None,
    audio_path: str | None = None,
    urls: list[str] | None = None,
    email_headers: dict | None = None,
    user=None,
    pref_languages: list[str] | None = None,
) -> dict:
    state: dict = {
        "source": source,
        "raw_text": raw_text or "",
        "image_bytes": image_bytes,
        "audio_path": audio_path,
        "urls": urls or [],
        "email_headers": email_headers,
        "pref_languages": pref_languages or (member_service.langs_of(user) if user else None),
    }

    result = await get_graph().ainvoke(state)

    # A natural-language language change short-circuits scam analysis.
    if result.get("intent") == "set_language":
        langs = result.get("pref_languages") or []
        if user is not None and langs:
            await member_service.set_language(session, user, langs)
        return {"intent": "set_language", "message": result.get("note"), "languages": langs}

    verdict: Verdict = result.get("verdict")

    report = Report(
        user_id=user.id if user else None,
        channel=source.get("channel", "web"),
        modality=result.get("modality", "text"),
        sender=source.get("sender_raw"),
        subject=source.get("subject"),
        raw_text=(raw_text or "")[:5000],
        extracted_text="\n".join(result.get("extracted_text") or [])[:5000],
        source_url=(result.get("urls") or [None])[0],
        risk_level=verdict.risk_level,
        is_scam=verdict.is_scam,
        confidence=verdict.confidence,
        scam_category=verdict.scam_category,
        tactics=json.dumps(verdict.tactics, ensure_ascii=False),
        sender_analysis=(
            json.dumps(verdict.sender_analysis.model_dump(), ensure_ascii=False)
            if verdict.sender_analysis
            else None
        ),
        input_language=verdict.input_language,
        verdict=verdict.model_dump_json(),
    )
    session.add(report)
    await session.commit()
    await session.refresh(report)

    alerted = 0
    if bot is not None and await alert_service.should_alert(verdict):
        alerted = await alert_service.alert(session, bot, verdict, source, report)

    return {"intent": "check", "verdict": verdict, "report_id": report.id, "alerted": alerted}
