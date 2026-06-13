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

from app.core.config import settings
from app.core.db import async_session_factory
from app.services import check_service

log = logging.getLogger("scamguardian.email")

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


def _fetch_unseen_sync() -> list[dict]:
    conn = imaplib.IMAP4_SSL(settings.EMAIL_IMAP_HOST)
    out: list[dict] = []
    try:
        conn.login(settings.EMAIL_IMAP_USER, settings.EMAIL_IMAP_PASSWORD)
        conn.select("INBOX")
        typ, data = conn.search(None, "UNSEEN")
        if typ != "OK":
            return out
        for num in data[0].split():
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
                }
            )
            conn.store(num, "+FLAGS", "\\Seen")
    finally:
        try:
            conn.logout()
        except Exception:
            pass
    return out


async def _poll_once(bot) -> int:
    messages = await asyncio.to_thread(_fetch_unseen_sync)
    for m in messages:
        async with async_session_factory() as session:
            result = await check_service.run_check(
                session=session,
                bot=bot,
                source={
                    "channel": "email",
                    "sender_raw": m["sender"],
                    "subject": m["subject"],
                    "elder_id": settings.email_owner_elder_id,
                },
                raw_text=m["body"],
                email_headers=m["headers"],
            )
        v = result.get("verdict")
        if v:
            log.info("email checked: from=%s risk=%s scam=%s alerted=%s", m["sender"], v.risk_level, v.is_scam, result.get("alerted"))
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
