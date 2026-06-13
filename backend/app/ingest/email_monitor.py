"""Channel B — autonomous Gmail monitoring (PLAN §7).

Polls the inbox over IMAP (App Password) every EMAIL_POLL_SECONDS for UNSEEN mail, runs
each through the SAME agent, and — if it's a scam — fires the family+elder alert. Email
HTML is attacker-controlled, so we strip it to plain text before the agent sees it.
"""
from __future__ import annotations

import asyncio
import email
import imaplib
import logging
from email.header import decode_header, make_header

from bs4 import BeautifulSoup

from app.bot import lang_buttons
from app.bot.replies import format_verdict
from app.core.config import settings
from app.core.db import async_session_factory
from app.services import alert_service, check_service, member_service

log = logging.getLogger("scamguardian.email")

# Live progress shown to the inbox owner while an email is checked (status msg edited in place).
_PROGRESS_STEPS = {
    "link_intel": "🌐 Opened the email's link safely & checked the domain…",
    "verify": "🔬 Inspecting the sender address for fakery…",
    "synthesize": "✍️ Deciding if it's a scam…",
}

_HEADERS_WE_KEEP = {"from", "reply-to", "return-path", "subject", "to", "authentication-results", "arc-authentication-results"}


def _decode(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def _extract_body(msg: email.message.Message) -> str:
    plain, html = "", ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if part.get_content_disposition() == "attachment":
                continue
            try:
                payload = part.get_payload(decode=True)
                if payload is None:
                    continue
                charset = part.get_content_charset() or "utf-8"
                text = payload.decode(charset, errors="replace")
            except Exception:
                continue
            if ctype == "text/plain" and not plain:
                plain = text
            elif ctype == "text/html" and not html:
                html = text
    else:
        try:
            payload = msg.get_payload(decode=True)
            text = payload.decode(msg.get_content_charset() or "utf-8", errors="replace") if payload else ""
        except Exception:
            text = ""
        if msg.get_content_type() == "text/html":
            html = text
        else:
            plain = text

    body = plain or (BeautifulSoup(html, "html.parser").get_text(" ", strip=True) if html else "")
    return body[:5000]


def _friendly_folder(folder: str) -> str:
    return "Spam" if "spam" in folder.lower() or "junk" in folder.lower() else "Inbox"


def _fetch_unseen_sync() -> list[dict]:
    conn = imaplib.IMAP4_SSL(settings.EMAIL_IMAP_HOST)
    out: list[dict] = []
    cap = settings.EMAIL_MAX_PER_POLL
    try:
        conn.login(settings.EMAIL_IMAP_USER, settings.EMAIL_IMAP_PASSWORD)
        for folder in settings.email_folders:  # e.g. INBOX, [Gmail]/Spam
            if len(out) >= cap:
                break
            try:
                typ, _ = conn.select(f'"{folder}"')  # quote names with special chars
                if typ != "OK":
                    continue
            except Exception:
                continue
            typ, data = conn.search(None, "UNSEEN")
            if typ != "OK" or not data or not data[0]:
                continue
            for num in data[0].split():
                if len(out) >= cap:
                    break
                typ, msg_data = conn.fetch(num, "(RFC822)")
                if typ != "OK" or not msg_data or not msg_data[0]:
                    continue
                msg = email.message_from_bytes(msg_data[0][1])
                headers = {k.lower(): _decode(v) for k, v in msg.items() if k.lower() in _HEADERS_WE_KEEP}
                out.append(
                    {
                        "headers": headers,
                        "sender": _decode(msg.get("From")),
                        "subject": _decode(msg.get("Subject")),
                        "body": _extract_body(msg),
                        "folder": _friendly_folder(folder),
                    }
                )
                conn.store(num, "+FLAGS", "\\Seen")
    finally:
        try:
            conn.logout()
        except Exception:
            pass
    return out


async def _handle_email(bot, session, m: dict) -> None:
    source = {
        "channel": "email",
        "sender_raw": m["sender"],
        "subject": m["subject"],
        "elder_id": settings.email_owner_elder_id,
    }
    elder = await member_service.get_user(session, settings.email_owner_elder_id)
    elder_chat = elder.telegram_chat_id if elder else None
    langs = member_service.langs_of(elder) if elder else ["en", "zh"]

    # 1) Immediately tell the watcher (inbox owner) an email is being checked.
    folder = m.get("folder", "Inbox")
    active = langs[0] if langs else "en"
    sender = m["sender"] or "unknown sender"
    intro = {
        "en": f"📧 New email in {folder} from {sender} — checking it now…",
        "zh": f"📧 {'垃圾邮件箱' if folder == 'Spam' else '收件箱'}收到一封来自 {sender} 的新邮件，正在检查…",
        "ms": f"📧 E-mel baharu dalam {folder} daripada {sender} — sedang memeriksa…",
        "ta": f"📧 {folder} இல் {sender} இடமிருந்து புதிய மின்னஞ்சல் — சரிபார்க்கிறேன்…",
    }.get(active, f"📧 New email in {folder} from {sender} — checking it now…")

    status = None
    if bot is not None and elder_chat:
        try:
            status = await bot.send_message(chat_id=elder_chat, text=intro)
        except Exception:
            status = None

    async def progress(node: str) -> None:
        if status is None:
            return
        label = _PROGRESS_STEPS.get(node)
        if not label:
            return
        try:
            await bot.edit_message_text(label, chat_id=elder_chat, message_id=status.message_id)
        except Exception:
            pass

    # 2) Run the agent (bot=None → no auto-alert; we drive the messaging here).
    result = await check_service.run_check(
        session=session,
        bot=None,
        source=source,
        raw_text=m["body"],
        email_headers=m["headers"],
        progress=progress if status is not None else None,
    )
    v = result.get("verdict")

    # 3) Show the watcher the verdict (edit the status message in place) + language buttons.
    if status is not None and v is not None:
        try:
            await bot.edit_message_text(
                format_verdict(v, langs),
                chat_id=elder_chat,
                message_id=status.message_id,
                reply_markup=lang_buttons.keyboard(),
            )
            lang_buttons.remember(elder_chat, status.message_id, {"kind": "verdict", "verdict": v})
        except Exception:
            pass

    # 4) On a scam, alert the guardians (the elder already saw it above).
    alerted = 0
    if bot is not None and v is not None and await alert_service.should_alert(v):
        alerted = await alert_service.alert(session, bot, v, source, include_elder=False)

    if v is not None:
        log.info("email checked: from=%s risk=%s scam=%s guardians_alerted=%s", m["sender"], v.risk_level, v.is_scam, alerted)


async def _poll_once(bot) -> int:
    messages = await asyncio.to_thread(_fetch_unseen_sync)
    for m in messages:
        async with async_session_factory() as session:
            await _handle_email(bot, session, m)
    return len(messages)


async def run_monitor(bot, stop_event: asyncio.Event) -> None:
    if not settings.email_configured:
        log.warning("Email monitor disabled: EMAIL_IMAP_USER / EMAIL_IMAP_PASSWORD not set.")
        return
    log.info("Email monitor started on %s (every %ss).", settings.EMAIL_IMAP_USER, settings.EMAIL_POLL_SECONDS)
    while not stop_event.is_set():
        try:
            await _poll_once(bot)
        except Exception as e:  # keep the loop alive across transient IMAP errors
            log.error("email poll error: %s", e)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=settings.EMAIL_POLL_SECONDS)
        except asyncio.TimeoutError:
            pass
