#!/usr/bin/env python3
"""Backfill missing rows in doctors for users with role=DOCTOR.

Usage:
  cd backend
  python scripts/backfill_doctors.py --dry-run
  python scripts/backfill_doctors.py
  python scripts/backfill_doctors.py --limit 50 --verbose
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Sequence

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import settings


MISSING_DOCTORS_SQL = text(
    """
    SELECT u.id AS user_id, u.email
    FROM users u
    LEFT JOIN doctors d ON d.user_id = u.id
    WHERE u.role = 'DOCTOR' AND d.id IS NULL
    ORDER BY u.created_at ASC
    LIMIT :limit
    """
)

INSERT_DOCTOR_SQL = text(
    """
    INSERT INTO doctors (id, user_id, is_active)
    VALUES (gen_random_uuid(), :user_id, true)
    ON CONFLICT (user_id) DO NOTHING
    """
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill missing doctor profiles")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print missing rows, do not write to database",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10000,
        help="Maximum number of missing rows to process (default: 10000)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print each affected user",
    )
    return parser.parse_args()


def fetch_missing(session: Session, limit: int) -> Sequence[dict[str, Any]]:
    rows = session.execute(MISSING_DOCTORS_SQL, {"limit": limit}).mappings().all()
    return rows


def main() -> int:
    args = parse_args()

    if args.limit <= 0:
        print("Error: --limit must be > 0", file=sys.stderr)
        return 2

    engine = create_engine(settings.DATABASE_URL_SYNC)

    created = 0
    with Session(engine) as session:
        missing = fetch_missing(session, args.limit)
        print(f"Found users with role DOCTOR and no profile: {len(missing)}")

        if args.verbose and missing:
            for row in missing:
                print(f" - {row['user_id']} | {row['email']}")

        if args.dry_run:
            print("Dry-run mode: no changes written.")
            return 0

        for row in missing:
            session.execute(INSERT_DOCTOR_SQL, {"user_id": str(row["user_id"])})
            created += 1

        session.commit()

    print(f"Created doctor profiles: {created}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

