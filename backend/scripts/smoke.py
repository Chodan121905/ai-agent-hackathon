"""End-to-end smoke test of every live subsystem. Run: `python scripts/smoke.py`.

Reads everything from .env. Prints PASS/FAIL per check and never prints secrets.
Safe to re-run (writes a couple of demo rows to scamguardian.db).
"""
from __future__ import annotations

import asyncio
import imaplib

from app.core.config import settings


def _line(ok: bool, name: str, detail: str = "") -> None:
    print(f"{'✅ PASS' if ok else '❌ FAIL'}  {name:<22} {detail}")


async def check_telegram() -> None:
    if not settings.telegram_configured:
        _line(False, "Telegram", "TELEGRAM_BOT_TOKEN not set")
        return
    try:
        from telegram import Bot

        async with Bot(settings.TELEGRAM_BOT_TOKEN) as bot:
            me = await bot.get_me()
        _line(True, "Telegram bot", f"@{me.username} (id {me.id})")
    except Exception as e:
        _line(False, "Telegram bot", repr(e)[:160])


async def check_llm() -> None:
    if not settings.llm_configured:
        _line(False, "LLM (Kimi)", "LLM_API_KEY not set")
        return
    try:
        from app.agent.llm import make_llm

        resp = await make_llm("triage").ainvoke(
            [{"role": "user", "content": "Reply with exactly one word: OK"}]
        )
        text = (getattr(resp, "content", "") or "").strip()
        _line(bool(text), "LLM (Kimi)", f"model={settings.LLM_MODEL_BRAIN} reply={text[:30]!r}")
    except Exception as e:
        _line(False, "LLM (Kimi)", repr(e)[:160])


async def check_imap() -> None:
    if not settings.email_configured:
        _line(False, "Gmail IMAP", "EMAIL_IMAP_USER/PASSWORD not set")
        return

    def _login_count():
        c = imaplib.IMAP4_SSL(settings.EMAIL_IMAP_HOST)
        try:
            c.login(settings.EMAIL_IMAP_USER, settings.EMAIL_IMAP_PASSWORD)
            c.select("INBOX")
            total = len(c.search(None, "ALL")[1][0].split())
            unseen = len(c.search(None, "UNSEEN")[1][0].split())
            return total, unseen
        finally:
            try:
                c.logout()
            except Exception:
                pass

    try:
        total, unseen = await asyncio.to_thread(_login_count)
        _line(True, "Gmail IMAP", f"{settings.EMAIL_IMAP_USER}: {total} total, {unseen} unread")
    except Exception as e:
        _line(False, "Gmail IMAP", repr(e)[:160])


async def check_agent_text() -> None:
    from app.core.db import async_session_factory, init_db
    from app.services import check_service

    await init_db()
    try:
        async with async_session_factory() as s:
            res = await check_service.run_check(
                session=s,
                bot=None,
                source={"channel": "web"},
                raw_text=(
                    "DBS Bank: your account is suspended. Verify now at "
                    "http://dbs-secure-verify.ru or it will be closed in 24 hours."
                ),
            )
        v = res["verdict"]
        _line(
            v.is_scam,
            "Agent (text+LLM)",
            f"risk={v.risk_level} scam={v.is_scam} conf={v.confidence:.2f} cat={v.scam_category}",
        )
        print(f"        EN: {v.explanation_en[:90]}")
        print(f"        ZH: {v.explanation_zh[:40]} ... ({len(v.explanation_zh)} chars)")
    except Exception as e:
        _line(False, "Agent (text+LLM)", repr(e)[:200])


async def check_agent_email_impostor() -> None:
    from app.core.db import async_session_factory
    from app.services import check_service

    try:
        async with async_session_factory() as s:
            res = await check_service.run_check(
                session=s,
                bot=None,
                source={
                    "channel": "email",
                    "sender_raw": '"DBS Bank" <alerts@dbs-verify.ru>',
                    "subject": "Account suspended",
                },
                raw_text="Dear customer, your account is suspended. Click the link to verify.",
                email_headers={
                    "From": '"DBS Bank" <alerts@dbs-verify.ru>',
                    "Subject": "Account suspended",
                },
            )
        v = res["verdict"]
        sa = v.sender_analysis
        _line(
            v.is_scam and v.risk_level == "high",
            "Agent (email impostor)",
            f"risk={v.risk_level} scam={v.is_scam} conf={v.confidence:.2f}",
        )
        if sa:
            print(
                f"        forensics: display_mismatch={sa.display_name_mismatch} "
                f"lookalike={sa.lookalike_domain} brand={sa.claimed_brand}"
            )
    except Exception as e:
        _line(False, "Agent (email impostor)", repr(e)[:200])


async def check_brightdata() -> None:
    if not settings.BRIGHTDATA_API_TOKEN:
        _line(False, "Bright Data", "token not set (optional)")
        return
    try:
        from app.integrations import brightdata

        intel = await brightdata.domain_intel("http://dbs-secure-verify.ru")
        ok = intel.get("configured") is True
        _line(ok, "Bright Data", f"domain={intel.get('domain')} keys={list(intel.keys())}")
    except Exception as e:
        _line(False, "Bright Data", repr(e)[:160])


def check_optional_sdks() -> None:
    for name, mod, extra in [
        ("faster-whisper", "faster_whisper", "stt"),
        ("daytona", "daytona_sdk", "daytona"),
        ("videodb", "videodb", "videodb"),
    ]:
        try:
            __import__(mod)
            _line(True, f"opt:{name}", "installed")
        except Exception:
            _line(False, f"opt:{name}", f'not installed (pip install -e ".[{extra}]")')


async def main() -> None:
    print("=" * 64)
    print("Scam Guardian — smoke test")
    print("=" * 64)
    print(f"  chinese={settings.chinese_label}  alert_elder_too={settings.ALERT_ELDER_TOO}")
    print("-" * 64)
    await check_telegram()
    await check_llm()
    await check_imap()
    await check_brightdata()
    await check_agent_text()
    await check_agent_email_impostor()
    print("-" * 64)
    check_optional_sdks()
    print("=" * 64)


if __name__ == "__main__":
    asyncio.run(main())
