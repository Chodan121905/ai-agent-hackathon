"""Verified-allowlist logic + member language preference (PLAN §11)."""
from __future__ import annotations

from sqlmodel import select

from app.core.config import settings
from app.models.tables import User


def langs_of(user: User | None) -> list[str]:
    if user is None or not user.language or user.language == "both":
        return settings.default_languages
    return [c.strip() for c in user.language.split(",") if c.strip()]


async def get_user(session, user_id: int | None) -> User | None:
    if not user_id:
        return None
    return await session.get(User, user_id)


async def get_by_telegram_user_id(session, telegram_user_id: int) -> User | None:
    res = await session.execute(select(User).where(User.telegram_user_id == telegram_user_id))
    return res.scalar_one_or_none()


async def get_or_create_telegram_user(
    session, telegram_user_id: int, chat_id: int | None = None, name: str | None = None
) -> User:
    user = await get_by_telegram_user_id(session, telegram_user_id)
    if user is None:
        is_admin = settings.admin_id is not None and telegram_user_id == settings.admin_id
        user = User(
            telegram_user_id=telegram_user_id,
            telegram_chat_id=chat_id,
            name=name,
            is_admin=is_admin,
            verified=is_admin,  # the admin is auto-verified
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    changed = False
    if chat_id and user.telegram_chat_id != chat_id:
        user.telegram_chat_id = chat_id
        changed = True
    if name and user.name != name:
        user.name = name
        changed = True
    if changed:
        await session.commit()
        await session.refresh(user)
    return user


async def set_verified(session, user: User, value: bool = True) -> User:
    user.verified = value
    await session.commit()
    await session.refresh(user)
    return user


async def set_verified_by_id(session, telegram_user_id: int, value: bool = True) -> User | None:
    user = await get_by_telegram_user_id(session, telegram_user_id)
    if user is None and value:
        user = User(telegram_user_id=telegram_user_id, verified=True)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user
    if user is None:
        return None
    return await set_verified(session, user, value)


async def set_language(session, user: User, langs: list[str]) -> User:
    if set(langs) == {"en", "zh"} or not langs:
        user.language = "both"
    else:
        user.language = ",".join(langs)
    await session.commit()
    await session.refresh(user)
    return user
