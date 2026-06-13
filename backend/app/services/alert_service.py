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


async def alert(session, bot, verdict: Verdict, source: dict, report=None, include_elder: bool = True) -> int:
    """Send the bilingual alert to all recipients. Returns the number of messages sent.

    include_elder=False when the elder has already been shown the verdict directly (e.g. the
    email monitor shows them live progress + result), so only the guardians are alerted.
    """
    from app.bot.replies import format_alert  # local import avoids a cycle

    elder = await _resolve_elder(session, source)
    recipients = []  # list[User]
    if elder:
        recipients += await guardian_service.active_guardians_for_elder(session, elder.id)
        if include_elder and settings.ALERT_ELDER_TOO and elder.telegram_chat_id:
            recipients.append(elder)

    if not recipients:
        return 0

    who = (elder.name if elder and elder.name else None) or "your family member"

    sent = 0
    seen: set[int] = set()
    for u in recipients:
        cid = u.telegram_chat_id
        if not cid or cid in seen:
            continue
        seen.add(cid)
        # each person gets the alert in THEIR active language
        text = format_alert(verdict, who, source, member_service.langs_of(u))
        try:
            await bot.send_message(chat_id=cid, text=text)
            sent += 1
        except Exception:
            pass
    return sent
