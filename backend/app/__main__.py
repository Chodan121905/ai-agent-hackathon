"""Entry point: `python -m app`.

Boots ONE process that runs everything (FastAPI API + Telegram bot long-polling +
autonomous email monitor). The bot and email poller are started from the FastAPI
lifespan in app.main, so a single uvicorn server is all we need.
"""
from __future__ import annotations

import uvicorn

from app.core.config import settings


def main() -> None:
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
