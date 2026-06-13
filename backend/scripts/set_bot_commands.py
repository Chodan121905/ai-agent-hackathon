"""Set the bot's slash-command menu + description. Run once: `python scripts/set_bot_commands.py`."""
from __future__ import annotations

import asyncio

from telegram import Bot, BotCommand

from app.core.config import settings

COMMANDS = [
    BotCommand("start", "Start / re-show the welcome"),
    BotCommand("verify", "Enter your access code: /verify <code>"),
    BotCommand("help", "How to use Scam Guardian"),
    BotCommand("invite", "Get a code to link a family member"),
    BotCommand("guardian", "Link yourself as a guardian: /guardian <code>"),
    BotCommand("lang", "Set reply language: /lang en|zh|both|ms|ta"),
]


async def main() -> None:
    if not settings.telegram_configured:
        raise SystemExit("TELEGRAM_BOT_TOKEN not set in .env")
    bot = Bot(settings.TELEGRAM_BOT_TOKEN)
    async with bot:
        await bot.set_my_commands(COMMANDS)
        await bot.set_my_description(
            "Scam Guardian — forward a suspicious text, screenshot, voice note, or link and "
            "get a bilingual (EN+中文) verdict. Family is alerted on high-risk scams."
        )
    print("✓ Bot commands + description set.")


if __name__ == "__main__":
    asyncio.run(main())
