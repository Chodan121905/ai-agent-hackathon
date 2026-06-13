"""The one brain entry point (PLAN §4). Telegram forwards, the email poller, and the REST
/check endpoint all call this. Runs the agent, persists a report, and (if a bot is given
and the verdict is high enough) fires the family alert.

Streams the graph node-by-node so callers (the Telegram bot) can show live progress, and
handles the two non-scam intents: set_language and chat (companion, with per-person memory).
"""
from __future__ import annotations

import json
from collections.abc import Awaitable, Callable

from app.agent.graph import get_graph
from app.agent.verdict import Verdict
from app.models.tables import Report
from app.services import alert_service, member_service, memory_store


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
    person_key: str | None = None,
    progress: Callable[[str], Awaitable[None]] | None = None,
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
    if person_key is not None:
        state["person_key"] = person_key
        state["memory"] = memory_store.load(person_key)

    # Stream node-by-node so the caller can report progress; accumulate the final state.
    final: dict = {}
    async for update in get_graph().astream(state, stream_mode="updates"):
        for node, payload in update.items():
            if progress is not None:
                await progress(node)
            if payload:
                final.update(payload)

    # A natural-language language change short-circuits scam analysis.
    if final.get("intent") == "set_language":
        langs = final.get("pref_languages") or []
        if user is not None and langs:
            await member_service.set_language(session, user, langs)
        return {"intent": "set_language", "message": final.get("note"), "languages": langs}

    # Companion chat — persist memory, no report, no alert.
    if final.get("intent") in ("chat", "help"):
        if person_key is not None and final.get("memory_out"):
            memory_store.save(person_key, final["memory_out"])
        return {"intent": "chat", "reply": final.get("chat_reply") or "I'm here for you."}

    verdict: Verdict = final.get("verdict")

    report = Report(
        user_id=user.id if user else None,
        channel=source.get("channel", "web"),
        modality=final.get("modality", "text"),
        sender=source.get("sender_raw"),
        subject=source.get("subject"),
        raw_text=(raw_text or "")[:5000],
        extracted_text="\n".join(final.get("extracted_text") or [])[:5000],
        source_url=(final.get("urls") or [None])[0],
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
