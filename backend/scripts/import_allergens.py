#!/usr/bin/env python3
"""Import allergens from alex2_allergens.csv into the allergens table.

CSV format (semicolon-separated):
  Категорія;Компонент/Екстракт;Код;Назва;Міжнародна номенклатура;Компонент;Біохімічна група

Usage:
  cd backend
  python scripts/import_allergens.py scripts/alex2_allergens.csv
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


def import_allergens(file_path: str) -> None:
    source_path = Path(file_path)
    if not source_path.is_absolute():
        for candidate in [Path.cwd() / file_path, Path(__file__).parent / file_path]:
            if candidate.exists():
                source_path = candidate
                break

    if not source_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    print(f"Reading {source_path} ...")

    records = []
    with open(source_path, encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=";")
        for row in reader:
            if len(row) < 4:
                continue
            category = row[0].strip()
            code = row[2].strip()
            name_ua = row[3].strip()
            international_name = row[4].strip() if len(row) > 4 else None
            component = row[5].strip() if len(row) > 5 else None

            # Skip header rows from files that contain both a technical header
            # (Column1;Column2;...) and a localized header (Категорія;...).
            if category in {"Column1", "Категорія"} or code in {"Column3", "Код"} or name_ua in {"Column4", "Назва"}:
                continue

            if not code or not name_ua:
                continue

            records.append({
                "category": category or None,
                "code": code,
                "name_ua": name_ua,
                "international_name": international_name or None,
                "component": component or None,
            })

    total = len(records)
    print(f"Extracted {total} allergen records from CSV.")

    engine = create_engine(settings.DATABASE_URL_SYNC)
    imported = 0
    skipped = 0

    with Session(engine) as session:
        for rec in records:
            session.execute(
                text(
                    """INSERT INTO allergens (id, code, name_ua, category, international_name, component, is_active)
                       VALUES (:id, :code, :name_ua, :category, :international_name, :component, true)
                       ON CONFLICT (code) DO NOTHING"""
                ),
                {
                    "id": str(uuid.uuid4()),
                    "code": rec["code"],
                    "name_ua": rec["name_ua"],
                    "category": rec["category"],
                    "international_name": rec["international_name"],
                    "component": rec["component"],
                },
            )
            imported += 1
        session.commit()

    print(f"Done. Imported: {imported}, skipped (duplicates): {skipped}.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_allergens.py <alex2_allergens.csv>")
        print("  Example: python scripts/import_allergens.py scripts/alex2_allergens.csv")
        sys.exit(1)

    try:
        import_allergens(sys.argv[1])
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)