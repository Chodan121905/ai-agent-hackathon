"""FastAPI dependencies."""
from __future__ import annotations

from app.core.db import get_session

__all__ = ["get_session"]
