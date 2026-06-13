"""Real Telegram bot (long polling) with a verified-members gate (PLAN §11).

Two modes, both always on:
  • Interactive — a verified member sends/forwards text, a screenshot, a voice note, or
    pastes a link, and gets a bilingual verdict back.
  • Autonomous — the email monitor pushes alerts independently (see ingest/email_monitor).
The same process runs both.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    ApplicationHandlerStop,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    TypeHandler,
    filters,
)

from app.core.config import settings
from app.core.db import async_session_factory
from app.bot.replies import format_verdict
from app.services import check_service, guardian_service, member_service

_NOT_AUTHORIZED = (
    "🔒 Not authorized yet. Please enter your access code:\n"
    "/verify <code>\n\n"
    "🔒 尚未授权。请输入访问码：/verify <代码>"
)

# Live progress shown while a slow check runs (status message is edited in place).
_PROGRESS_STEPS = {
    "ocr": "✅ Read the text in your image…",
    "transcribe": "✅ Transcribed your voice note…",
    "link_intel": "✅ Opened the link safely & checked the domain…",
    "analyze": "🧠 Analysing the content for scam tactics…",
    "verify": "🔬 Verifying the sender & links…",
    "synthesize": "✍️ Writing your verdict…",
}


# ───────────────────────── verification gate (runs first) ─────────────────────────
async def _gate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    msg = update.effective_message
    if tg_user is None or msg is None:
        return
    text = (msg.text or "").strip()
    allowed_unverified = text.startswith("/start") or text.startswith("/verify")
    async with async_session_factory() as session:
        user = await member_service.get_or_create_telegram_user(
            session, tg_user.id, msg.chat_id, tg_user.full_name
        )
        if user.verified or allowed_unverified:
            return
    await msg.reply_text(_NOT_AUTHORIZED)
    raise ApplicationHandlerStop


# ───────────────────────── commands ─────────────────────────
async def _start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    async with async_session_factory() as session:
        user = await member_service.get_or_create_telegram_user(
            session, tg_user.id, update.effective_chat.id, tg_user.full_name
        )
        verified = user.verified
    if verified:
        await update.message.reply_text(
            "🛡️ Welcome to Scam Guardian.\nForward me any suspicious text, screenshot, voice note, "
            "or link and I'll tell you if it's a scam — in English and 中文.\n\n"
            "🛡️ 欢迎使用「防诈卫士」。把任何可疑的短信、截图、语音或链接转发给我，"
            "我会用中英双语告诉你是不是诈骗。"
        )
    else:
        await update.message.reply_text(
            "🛡️ Welcome to Scam Guardian.\nThis bot is for approved family members only.\n"
            "Please enter your access code:  /verify <code>\n\n"
            "🛡️ 欢迎使用「防诈卫士」。本机器人仅限已批准的家庭成员使用。\n"
            "请输入访问码：/verify <代码>"
        )


async def _verify(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    code = " ".join(context.args).strip() if context.args else ""
    tg_user = update.effective_user
    if code != settings.ACCESS_CODE:
        await update.message.reply_text("❌ Wrong code. Please try again: /verify <code>\n❌ 访问码错误，请重试。")
        return
    async with async_session_factory() as session:
        user = await member_service.get_or_create_telegram_user(
            session, tg_user.id, update.effective_chat.id, tg_user.full_name
        )
        await member_service.set_verified(session, user, True)
    await update.message.reply_text(
        "✅ You're verified! Forward me anything suspicious and I'll check it.\n"
        "✅ 验证成功！把任何可疑信息转发给我即可。"
    )


async def _help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🛡️ Scam Guardian — how to use:\n"
        "• Forward a text, screenshot, voice note, or paste a link → I check it.\n"
        "• Say 'reply in English' / '用中文回答' to change language.\n"
        "• /invite — get a code to link a family member.\n"
        "• /guardian <code> — link yourself as a guardian.\n\n"
        "🛡️ 用法：转发短信/截图/语音或粘贴链接即可；说“用英文回答”可切换语言；"
        "/invite 生成家人配对码；/guardian <码> 绑定为监护人。"
    )


async def _invite(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    async with async_session_factory() as session:
        user = await member_service.get_or_create_telegram_user(session, tg_user.id, update.effective_chat.id)
        link = await guardian_service.create_invite(session, user)
    await update.message.reply_text(
        f"👨‍👩‍👧 Share this code with your family member. They open this bot and send:\n"
        f"/guardian {link.pairing_code}\n\n"
        f"👨‍👩‍👧 把这个配对码发给你的家人，让他们打开本机器人并发送：/guardian {link.pairing_code}"
    )


async def _guardian(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    code = (context.args[0] if context.args else "").strip()
    if not code:
        await update.message.reply_text("Usage: /guardian <code>\n用法：/guardian <配对码>")
        return
    tg_user = update.effective_user
    async with async_session_factory() as session:
        user = await member_service.get_or_create_telegram_user(session, tg_user.id, update.effective_chat.id, tg_user.full_name)
        link = await guardian_service.claim(session, code, user)
    if link is None:
        await update.message.reply_text("❌ Invalid or used code.\n❌ 配对码无效或已被使用。")
    else:
        await update.message.reply_text(
            "✅ Linked! You'll be alerted if your family member is targeted by a scam.\n"
            "✅ 绑定成功！当你的家人遭遇诈骗时，你会收到提醒。"
        )


async def _lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    choice = (context.args[0].lower() if context.args else "both")
    mapping = {"en": ["en"], "zh": ["zh"], "both": ["en", "zh"], "ms": ["ms"], "ta": ["ta"]}
    langs = mapping.get(choice, ["en", "zh"])
    tg_user = update.effective_user
    async with async_session_factory() as session:
        user = await member_service.get_or_create_telegram_user(session, tg_user.id, update.effective_chat.id)
        await member_service.set_language(session, user, langs)
    await update.message.reply_text(f"✅ Language set: {', '.join(langs)}\n✅ 语言已设置：{', '.join(langs)}")


async def _admin_set(update: Update, context: ContextTypes.DEFAULT_TYPE, value: bool) -> None:
    tg_user = update.effective_user
    if settings.admin_id is None or tg_user.id != settings.admin_id:
        await update.message.reply_text("Admin only. 仅管理员可用。")
        return
    if not context.args or not context.args[0].lstrip("-").isdigit():
        await update.message.reply_text("Usage: /approve <telegram_user_id>")
        return
    target = int(context.args[0])
    async with async_session_factory() as session:
        await member_service.set_verified_by_id(session, target, value)
    await update.message.reply_text(f"{'✅ Approved' if value else '🚫 Revoked'} user {target}.")


async def _approve(update, context):
    await _admin_set(update, context, True)


async def _revoke(update, context):
    await _admin_set(update, context, False)


# ───────────────────────── interactive message handler ─────────────────────────
def _extract_urls(msg) -> list[str]:
    urls: list[str] = []
    text = msg.text or ""
    caption = msg.caption or ""
    for ent in msg.entities or []:
        if ent.type == "url":
            urls.append(text[ent.offset : ent.offset + ent.length])
        elif ent.type == "text_link" and ent.url:
            urls.append(ent.url)
    for ent in msg.caption_entities or []:
        if ent.type == "url":
            urls.append(caption[ent.offset : ent.offset + ent.length])
        elif ent.type == "text_link" and ent.url:
            urls.append(ent.url)
    return urls


async def _on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    tg_user = update.effective_user
    text = msg.text or msg.caption or ""
    image_bytes: bytes | None = None
    audio_path: str | None = None
    urls = _extract_urls(msg)

    if msg.photo:
        f = await context.bot.get_file(msg.photo[-1].file_id)
        image_bytes = bytes(await f.download_as_bytearray())

    voice = msg.voice or msg.audio
    if voice:
        f = await context.bot.get_file(voice.file_id)
        tmp = Path(tempfile.gettempdir()) / f"sg_voice_{voice.file_unique_id}.ogg"
        await f.download_to_drive(custom_path=str(tmp))
        audio_path = str(tmp)

    heavy = bool(image_bytes or audio_path or urls)
    await context.bot.send_chat_action(chat_id=msg.chat_id, action="typing")

    status = {"msg": None}
    if heavy:
        status["msg"] = await msg.reply_text("🔎 On it — checking this for you…")

    async def progress(node: str) -> None:
        label = _PROGRESS_STEPS.get(node)
        if not label:
            return
        try:
            if status["msg"] is None:
                status["msg"] = await msg.reply_text(label)
            else:
                await status["msg"].edit_text(label)
        except Exception:
            pass

    langs = ["en", "zh"]
    try:
        async with async_session_factory() as session:
            user = await member_service.get_or_create_telegram_user(
                session, tg_user.id, msg.chat_id, tg_user.full_name
            )
            result = await check_service.run_check(
                session=session,
                bot=context.bot,
                source={"channel": "telegram", "telegram_user_id": tg_user.id, "who": tg_user.full_name},
                raw_text=text,
                image_bytes=image_bytes,
                audio_path=audio_path,
                urls=urls or None,
                user=user,
                person_key=str(tg_user.id),
                progress=progress,
            )
            langs = member_service.langs_of(user)
    finally:
        if audio_path:
            try:
                Path(audio_path).unlink(missing_ok=True)
            except Exception:
                pass

    intent = result.get("intent")
    if intent == "set_language":
        final_text = result.get("message") or "✅ Done."
    elif intent == "chat":
        final_text = result.get("reply") or "🙂"
    else:
        final_text = format_verdict(result["verdict"], langs)
        if result.get("alerted"):
            final_text += f"\n\n📣 Alerted {result['alerted']} family member(s)."

    if status["msg"] is not None:
        try:
            await status["msg"].edit_text(final_text)
        except Exception:
            await msg.reply_text(final_text)
    else:
        await msg.reply_text(final_text)


# ───────────────────────── build ─────────────────────────
def build_application() -> Application:
    app = ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(TypeHandler(Update, _gate), group=-1)
    app.add_handler(CommandHandler("start", _start))
    app.add_handler(CommandHandler("verify", _verify))
    app.add_handler(CommandHandler("help", _help))
    app.add_handler(CommandHandler("invite", _invite))
    app.add_handler(CommandHandler("guardian", _guardian))
    app.add_handler(CommandHandler("lang", _lang))
    app.add_handler(CommandHandler("approve", _approve))
    app.add_handler(CommandHandler("revoke", _revoke))
    app.add_handler(
        MessageHandler(
            (filters.TEXT & ~filters.COMMAND) | filters.PHOTO | filters.VOICE | filters.AUDIO,
            _on_message,
        )
    )
    return app
