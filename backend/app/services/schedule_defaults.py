from __future__ import annotations

import uuid
from datetime import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scheduling import Schedule

DEFAULT_WEEKDAYS = (0, 1, 2, 3, 4)  # Monday-Friday
DEFAULT_START_TIME = time(9, 0)
DEFAULT_END_TIME = time(18, 0)
DEFAULT_SLOT_DURATION_MIN = 20


async def ensure_default_doctor_schedule(db: AsyncSession, doctor_id: uuid.UUID) -> int:
    """Create a default weekly schedule when doctor has no active schedules.

    Returns the number of created schedule rows.
    """
    existing_result = await db.execute(
        select(Schedule.id)
        .where(
            Schedule.doctor_id == doctor_id,
            Schedule.is_active == True,
        )
        .limit(1)
    )
    if existing_result.scalar_one_or_none() is not None:
        return 0

    for day in DEFAULT_WEEKDAYS:
        db.add(
            Schedule(
                doctor_id=doctor_id,
                day_of_week=day,
                start_time=DEFAULT_START_TIME,
                end_time=DEFAULT_END_TIME,
                slot_duration=DEFAULT_SLOT_DURATION_MIN,
                is_active=True,
            )
        )

    await db.flush()
    return len(DEFAULT_WEEKDAYS)

