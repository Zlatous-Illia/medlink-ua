#!/usr/bin/env python3
"""Import drug records from reestr.csv (Ukrainian drug registry) into the database.

CSV format:
  - Encoding: cp1251 (Windows-1251)
  - Delimiter: semicolon (;)
  - Key columns (0-indexed):
      [0]  ID             — registry UUID (used as primary key for idempotent re-import)
      [1]  trade_name     — Повна торговельна назва
      [2]  inn            — Міжнародна непатентована назва (INN, required)
      [3]  form           — Форма випуску (e.g. "Таблетки по 300 мг")
      [5]  dosage         — Форма (форм): composition per unit
      [7]  atc_code       — АТС код 1
      [10] manufacturer   — Виробник: повна назва
"""
import sys
import csv
import uuid
import os
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.core.config import settings

ENCODING = "cp1251"
DELIMITER = ";"


def _to_uuid(raw_id: str) -> str:
    """Convert 32-char hex registry ID to standard UUID string."""
    try:
        return str(uuid.UUID(raw_id.strip()))
    except ValueError:
        return str(uuid.uuid4())


def import_drugs(file_path: str) -> None:
    source_path = Path(file_path)
    if not source_path.is_absolute():
        for candidate in [Path.cwd() / file_path, Path(__file__).parent / file_path]:
            if candidate.exists():
                source_path = candidate
                break

    if not source_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if source_path.suffix.lower() != ".csv":
        raise ValueError(f"Expected .csv file, got: {source_path.name}")

    print(f"Reading {source_path} (encoding={ENCODING}, delimiter='{DELIMITER}') ...")

    records = []
    with open(source_path, encoding=ENCODING, newline="") as f:
        reader = csv.reader(f, delimiter=DELIMITER)
        next(reader)  # skip header row
        for row in reader:
            # Pad row to at least 11 columns to avoid index errors
            while len(row) < 11:
                row.append("")

            raw_id    = row[0].strip()
            trade     = row[1].strip()[:255] or None
            inn       = row[2].strip()
            form      = row[3].strip()[:100] or None
            dosage    = row[5].strip()[:100] or None
            atc_code  = row[7].strip()[:10] or None
            mfr       = row[10].strip()[:255] or None

            records.append({
                "id":           _to_uuid(raw_id),
                "atc_code":     atc_code,
                "inn":          inn,
                "trade_name":   trade,
                "form":         form,
                "dosage":       dosage,
                "manufacturer": mfr,
            })

    total = len(records)
    print(f"Parsed {total} rows from CSV.")

    engine = create_engine(settings.DATABASE_URL_SYNC)
    imported = 0
    skipped = 0
    batch_size = 500

    with Session(engine) as session:
        for i in range(0, total, batch_size):
            batch = records[i:i + batch_size]
            for rec in batch:
                if not rec["inn"]:
                    skipped += 1
                    continue
                session.execute(
                    text(
                        """INSERT INTO drugs
                               (id, atc_code, inn, trade_name, form, dosage, manufacturer,
                                is_narcotic, is_active)
                           VALUES
                               (:id, :atc_code, :inn, :trade_name, :form, :dosage, :manufacturer,
                                false, true)
                           ON CONFLICT (id) DO NOTHING"""
                    ),
                    rec,
                )
                imported += 1
            session.commit()
            done = min(i + batch_size, total)
            print(f"  Processed {done} / {total} ...")

    print(f"Done. Imported: {imported}, skipped (no INN): {skipped}.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_drugs.py <reestr.csv>")
        print("  Example: python scripts/import_drugs.py scripts/reestr.csv")
        sys.exit(1)

    try:
        import_drugs(sys.argv[1])
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)
