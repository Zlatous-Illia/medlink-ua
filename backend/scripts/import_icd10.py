#!/usr/bin/env python3
"""Import ICD-10 codes from CSV or JSON file into the database."""
import sys
import csv
import json
import uuid
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.reference import ICD10Code
from app.core.database import Base


def import_icd10(file_path: str):
    engine = create_engine(settings.DATABASE_URL_SYNC)
    records = []

    if file_path.endswith(".json"):
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        for item in data:
            records.append({
                "code": item.get("code", ""),
                "name_ua": item.get("name_ua", ""),
                "name_en": item.get("name_en"),
                "category": item.get("category"),
            })
    else:
        with open(file_path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append({
                    "code": row.get("code", ""),
                    "name_ua": row.get("name_ua", ""),
                    "name_en": row.get("name_en") or None,
                    "category": row.get("category") or None,
                })

    total = len(records)
    imported = 0
    batch_size = 500

    with Session(engine) as session:
        for i in range(0, total, batch_size):
            batch = records[i:i + batch_size]
            for rec in batch:
                if not rec["code"] or not rec["name_ua"]:
                    continue
                session.execute(
                    text(
                        """INSERT INTO icd10_codes (id, code, name_ua, name_en, category, is_active)
                           VALUES (:id, :code, :name_ua, :name_en, :category, true)
                           ON CONFLICT (code) DO NOTHING"""
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "code": rec["code"],
                        "name_ua": rec["name_ua"],
                        "name_en": rec["name_en"],
                        "category": rec["category"],
                    },
                )
                imported += 1
            session.commit()
            print(f"Imported {min(i + batch_size, total)} / {total} records")

    print(f"Done. Total imported: {imported}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_icd10.py <file.csv|file.json>")
        sys.exit(1)
    import_icd10(sys.argv[1])
