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
from app.core.config import settings
from app.models.tables import Report
from app.services import alert_service, member_service, memory_store

_AUDIO_FAILED = {
    "en": "🎧 Sorry, I couldn't understand that voice message. Please try again, or type it out.",
    "zh": "🎧 抱歉，我没听清这条语音，请再说一次，或直接打字给我。",
    "ms": "🎧 Maaf, saya tidak faham mesej suara itu. Cuba lagi atau taipkannya.",
    "ta": "🎧 மன்னிக்கவும், அந்தக் குரல் செய்தியை என்னால் புரிந்துகொள்ள முடியவில்லை. மீண்டும் முயற்சிக்கவும் அல்லது தட்டச்சு செய்யவும்.",
}


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
        state["recent_checks"] = memory_store.load_checks(person_key)

    # Stream node-by-node so the caller can report progress; accumulate the final state.
    final: dict = {}
    async for update in get_graph().astream(state, stream_mode="updates"):
        for node, payload in update.items():
            if progress is not None:
                await progress(node)
            if payload:
                final.update(payload)

    # A voice note we couldn't transcribe → ask to retry, don't run a check on nothing.
    if final.get("audio_failed") and not (final.get("raw_text") or "").strip():
        active = (member_service.langs_of(user) if user else settings.default_languages)[0]
        return {"intent": "chat", "reply": _AUDIO_FAILED.get(active, _AUDIO_FAILED["en"])}

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

    # Record this analysis in the person's memory so the companion can answer follow-ups.
    if person_key is not None:
        memory_store.append_check(person_key, _check_summary(verdict, source, raw_text))

    alerted = 0
    if bot is not None and await alert_service.should_alert(verdict):
        alerted = await alert_service.alert(session, bot, verdict, source, report)

    return {"intent": "check", "verdict": verdict, "report_id": report.id, "alerted": alerted}


def _check_summary(verdict: Verdict, source: dict, raw_text: str) -> str:
    pct = round(verdict.confidence * 100)
    what = source.get("subject") or (raw_text or "").strip().replace("\n", " ")[:70] or "(no text)"
    sender = source.get("sender_raw") or (verdict.sender_analysis.from_address if verdict.sender_analysis else None)
    label = "SCAM" if verdict.is_scam else "likely safe"
    parts = [
        f"- [{label} {verdict.risk_level} {pct}%]",
        f'"{what}"',
    ]
    if sender:
        parts.append(f"from {sender}")
    if verdict.scam_category:
        parts.append(f"({verdict.scam_category})")
    if verdict.tactics:
        parts.append("tactics: " + ", ".join(verdict.tactics))
    # a short why, in English, for the companion to paraphrase in the active language
    parts.append("— " + (verdict.explanation_en or "")[:160])
    return " ".join(parts)
