"""FastAPI app + one-process lifespan (PLAN §16).

On startup: create SQLite tables → start the Telegram bot (long polling) → start the
autonomous email monitor. All inside ONE process. Ctrl+C stops everything.
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

from app.api.routers import check, email_accounts, guardians, intelligence, reports
from app.core.config import settings
from app.core.db import init_db

log = logging.getLogger("scamguardian")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    await init_db()

    app.state.bot_app = None
    app.state.stop_event = asyncio.Event()
    app.state.tasks = []

    bot = None
    if settings.telegram_configured:
        from app.bot.telegram_bot import build_application

        bot_app = build_application()
        await bot_app.initialize()
        await bot_app.start()
        await bot_app.updater.start_polling(drop_pending_updates=True)
        app.state.bot_app = bot_app
        bot = bot_app.bot
        log.info("Telegram bot started (long polling).")
    else:
        log.warning("Telegram disabled: TELEGRAM_BOT_TOKEN not set in .env.")

    if settings.email_configured:
        from app.ingest.email_monitor import run_monitor

        app.state.tasks.append(asyncio.create_task(run_monitor(bot, app.state.stop_event)))

    try:
        yield
    finally:
        app.state.stop_event.set()
        for t in app.state.tasks:
            t.cancel()
        if app.state.bot_app is not None:
            try:
                await app.state.bot_app.updater.stop()
                await app.state.bot_app.stop()
                await app.state.bot_app.shutdown()
            except Exception:
                pass
        log.info("Shutdown complete.")


def _unique_id(route: APIRoute) -> str:
    return route.name


app = FastAPI(
    title="Scam Guardian",
    version="0.1.0",
    description="Telegram + autonomous email scam detection (multi-phase LangGraph agent).",
    lifespan=lifespan,
    generate_unique_id_function=_unique_id,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API = "/api/v1"
app.include_router(check.router, prefix=API)
app.include_router(reports.router, prefix=API)
app.include_router(guardians.router, prefix=API)
app.include_router(email_accounts.router, prefix=API)
app.include_router(intelligence.router, prefix=API)


@app.get("/health", tags=["health"], operation_id="health")
async def health() -> dict:
    return {
        "status": "ok",
        "telegram": settings.telegram_configured,
        "email_monitor": settings.email_configured,
        "llm": settings.llm_configured,
        "chinese": settings.chinese_label,
        "alert_elder_too": settings.ALERT_ELDER_TOO,
    }
