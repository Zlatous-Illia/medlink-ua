#!/usr/bin/env python3
"""Import drug records from CSV file into the database."""
import sys
import csv
import uuid
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.core.config import settings


def import_drugs(file_path: str):
    engine = create_engine(settings.DATABASE_URL_SYNC)
    records = []

    with open(file_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append({
                "atc_code": row.get("atc_code") or None,
                "inn": row.get("inn", ""),
                "trade_name": row.get("trade_name") or None,
                "form": row.get("form") or None,
                "dosage": row.get("dosage") or None,
                "manufacturer": row.get("manufacturer") or None,
            })

    total = len(records)
    imported = 0
    batch_size = 500

    with Session(engine) as session:
        for i in range(0, total, batch_size):
            batch = records[i:i + batch_size]
            for rec in batch:
                if not rec["inn"]:
                    continue
                session.execute(
                    text(
                        """INSERT INTO drugs (id, atc_code, inn, trade_name, form, dosage, manufacturer, is_narcotic, is_active)
                           VALUES (:id, :atc_code, :inn, :trade_name, :form, :dosage, :manufacturer, false, true)
                           ON CONFLICT DO NOTHING"""
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "atc_code": rec["atc_code"],
                        "inn": rec["inn"],
                        "trade_name": rec["trade_name"],
                        "form": rec["form"],
                        "dosage": rec["dosage"],
                        "manufacturer": rec["manufacturer"],
                    },
                )
                imported += 1
            session.commit()
            print(f"Imported {min(i + batch_size, total)} / {total} records")

    print(f"Done. Total imported: {imported}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_drugs.py <file.csv>")
        sys.exit(1)
    import_drugs(sys.argv[1])
