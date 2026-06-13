"""Inline language-switch buttons attached to verdicts/alerts.

Two buttons — "Change to English" and "改用中文" (Change to Chinese, labelled in Chinese).
Tapping one sets the person's active language AND re-renders that message in the new
language. A small in-process cache remembers the Verdict behind each message so it can be
re-rendered (one process, session-lifetime; capped).
"""
from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

_CACHE: dict = {}
_ORDER: list = []
_CAP = 400


def keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("Change to English", callback_data="lang:en"),
            InlineKeyboardButton("改用中文", callback_data="lang:zh"),
        ]]
    )


def remember(chat_id: int, message_id: int, payload: dict) -> None:
    key = (chat_id, message_id)
    _CACHE[key] = payload
    _ORDER.append(key)
    while len(_ORDER) > _CAP:
        _CACHE.pop(_ORDER.pop(0), None)


def recall(chat_id: int, message_id: int) -> dict | None:
    return _CACHE.get((chat_id, message_id))
