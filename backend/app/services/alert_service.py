"""Family-alert dispatch (PLAN §7.5, §11). Fires on a forwarded high-risk item AND on a
scam email caught autonomously. Recipients = the elder's active guardians, plus the
elder too (locked decision: ALERT_ELDER_TOO)."""
from __future__ import annotations

from app.agent.verdict import Verdict
from app.core.config import settings
from app.services import guardian_service, member_service

_RISK_ORDER = {"low": 0, "medium": 1, "high": 2}


async def should_alert(verdict: Verdict) -> bool:
    threshold = _RISK_ORDER.get(settings.ALERT_THRESHOLD, 2)
    return verdict.is_scam and _RISK_ORDER.get(verdict.risk_level, 0) >= threshold


async def _resolve_elder(session, source: dict):
    if source.get("channel") == "email":
        elder_id = source.get("elder_id") or settings.email_owner_elder_id
        return await member_service.get_user(session, elder_id)
    tuid = source.get("telegram_user_id")
    return await member_service.get_by_telegram_user_id(session, tuid) if tuid else None


async def alert(session, bot, verdict: Verdict, source: dict, report=None) -> int:
    """Send the bilingual alert to all recipients. Returns the number of messages sent."""
    from app.bot.replies import format_alert  # local import avoids a cycle

    elder = await _resolve_elder(session, source)
    chat_ids: set[int] = set()

    if elder:
        for g in await guardian_service.active_guardians_for_elder(session, elder.id):
            chat_ids.add(g.telegram_chat_id)
        if settings.ALERT_ELDER_TOO and elder.telegram_chat_id:
            chat_ids.add(elder.telegram_chat_id)

    if not chat_ids:
        return 0

    who = (elder.name if elder and elder.name else None) or "your family member"
    text = format_alert(verdict, who=who, source=source)

    sent = 0
    for cid in chat_ids:
        try:
            await bot.send_message(chat_id=cid, text=text)
            sent += 1
        except Exception:
            pass
    return sent
