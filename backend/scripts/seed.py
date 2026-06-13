"""Optional demo seed: ensure an elder exists (id = EMAIL_OWNER_ELDER_ID) and add a couple
of sample reports so /intelligence/trends shows data. Run: `python scripts/seed.py`."""
from __future__ import annotations

import asyncio
import json

from app.core.db import async_session_factory, init_db
from app.models.tables import Report, User


async def main() -> None:
    await init_db()
    async with async_session_factory() as session:
        elder = await session.get(User, 1)
        if elder is None:
            session.add(User(id=1, name="Demo Elder", role="elder", verified=True))
        session.add(
            Report(
                user_id=1,
                channel="email",
                modality="email",
                sender='"DBS Bank" <alerts@dbs-verify.ru>',
                subject="Your account is suspended",
                raw_text="Your DBS account is suspended. Verify now.",
                risk_level="high",
                is_scam=True,
                confidence=0.92,
                scam_category="bank_impersonation",
                tactics=json.dumps(["authority_impersonation", "urgency", "display_name_mismatch"]),
                input_language="en",
                verdict="{}",
            )
        )
        await session.commit()
    print("✓ Seeded demo elder + sample report.")


if __name__ == "__main__":
    asyncio.run(main())
