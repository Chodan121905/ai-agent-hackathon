"""Family pairing loop (PLAN §11). A bot can't message someone who never /start-ed it,
so a guardian must claim a code, which captures their chat_id."""
from __future__ import annotations

import secrets

from sqlmodel import select

from app.models.tables import GuardianLink, User


async def create_invite(session, elder: User) -> GuardianLink:
    code = secrets.token_hex(3).upper()  # 6 hex chars
    link = GuardianLink(elder_id=elder.id, pairing_code=code, status="pending")
    session.add(link)
    await session.commit()
    await session.refresh(link)
    return link


async def claim(session, code: str, guardian: User) -> GuardianLink | None:
    res = await session.execute(
        select(GuardianLink).where(
            GuardianLink.pairing_code == code.strip().upper(),
            GuardianLink.status == "pending",
        )
    )
    link = res.scalar_one_or_none()
    if link is None:
        return None
    link.guardian_id = guardian.id
    link.status = "active"
    await session.commit()
    await session.refresh(link)
    return link


async def active_guardians_for_elder(session, elder_id: int) -> list[User]:
    res = await session.execute(
        select(GuardianLink).where(
            GuardianLink.elder_id == elder_id, GuardianLink.status == "active"
        )
    )
    links = res.scalars().all()
    guardians: list[User] = []
    for link in links:
        if link.guardian_id:
            g = await session.get(User, link.guardian_id)
            if g and g.telegram_chat_id:
                guardians.append(g)
    return guardians


async def list_for_elder(session, elder_id: int) -> list[GuardianLink]:
    res = await session.execute(select(GuardianLink).where(GuardianLink.elder_id == elder_id))
    return list(res.scalars().all())
