#!/usr/bin/env python3
"""Backfill default schedules for doctors without active schedules.

Usage:
  cd backend
  python scripts/backfill_doctor_schedules.py --dry-run
  python scripts/backfill_doctor_schedules.py
  python scripts/backfill_doctor_schedules.py --limit 100 --verbose
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import time
from typing import Any, Sequence

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import settings


DEFAULT_WEEKDAYS = (0, 1, 2, 3, 4)  # Monday-Friday
DEFAULT_START_TIME = time(9, 0)
DEFAULT_END_TIME = time(18, 0)
DEFAULT_SLOT_DURATION = 20

DOCTORS_WITHOUT_SCHEDULE_SQL = text(
    """
    SELECT d.id AS doctor_id, u.email
    FROM doctors d
    JOIN users u ON u.id = d.user_id
    LEFT JOIN schedules s ON s.doctor_id = d.id AND s.is_active = true
    WHERE d.is_active = true
    GROUP BY d.id, u.email
    HAVING COUNT(s.id) = 0
    ORDER BY u.email ASC
    LIMIT :limit
    """
)

INSERT_SCHEDULE_SQL = text(
    """
    INSERT INTO schedules (id, doctor_id, day_of_week, start_time, end_time, slot_duration, is_active)
    VALUES (gen_random_uuid(), :doctor_id, :day_of_week, :start_time, :end_time, :slot_duration, true)
    """
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill default doctor schedules")
    parser.add_argument("--dry-run", action="store_true", help="Print affected doctors only")
    parser.add_argument("--limit", type=int, default=10000, help="Maximum doctors to process")
    parser.add_argument("--verbose", action="store_true", help="Print each affected doctor")
    return parser.parse_args()


def fetch_doctors_without_schedule(session: Session, limit: int) -> Sequence[dict[str, Any]]:
    return session.execute(DOCTORS_WITHOUT_SCHEDULE_SQL, {"limit": limit}).mappings().all()


def main() -> int:
    args = parse_args()

    if args.limit <= 0:
        print("Error: --limit must be > 0", file=sys.stderr)
        return 2

    engine = create_engine(settings.DATABASE_URL_SYNC)

    created_rows = 0
    with Session(engine) as session:
        doctors = fetch_doctors_without_schedule(session, args.limit)
        print(f"Found active doctors without schedule: {len(doctors)}")

        if args.verbose and doctors:
            for row in doctors:
                print(f" - {row['doctor_id']} | {row['email']}")

        if args.dry_run:
            print("Dry-run mode: no changes written.")
            return 0

        for row in doctors:
            for day in DEFAULT_WEEKDAYS:
                session.execute(
                    INSERT_SCHEDULE_SQL,
                    {
                        "doctor_id": str(row["doctor_id"]),
                        "day_of_week": day,
                        "start_time": DEFAULT_START_TIME,
                        "end_time": DEFAULT_END_TIME,
                        "slot_duration": DEFAULT_SLOT_DURATION,
                    },
                )
                created_rows += 1

        session.commit()

    print(f"Created schedule rows: {created_rows}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

