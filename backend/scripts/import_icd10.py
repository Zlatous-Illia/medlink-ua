#!/usr/bin/env python3
"""Import ICD-10 codes from mkh10.json (hierarchical Ukrainian MKH-10 tree) into the database."""
import sys
import json
import uuid
import os
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.core.config import settings


def extract_records(data: dict) -> list[dict]:
    """Recursively traverse the mkh10.json tree and extract all leaf/disease codes.

    Tree structure:
        root.children  (dict of class nodes, no code)
          -> class node: {clazz, name_ua, children: dict of group nodes}
          -> group node: {code: "A00-A09", name_ua, children: dict of disease nodes}
          -> disease node: {code: "A00", name_ua, name_en, children: list of leaf nodes}
          -> leaf node (list item): {code: "A00.0", name_ua, name_en}

    category is set to the nearest parent range-code (e.g. "A00-A09").
    """
    records: list[dict] = []

    def walk(obj, category: str | None = None) -> None:
        if isinstance(obj, list):
            for item in obj:
                walk(item, category)
            return
        if not isinstance(obj, dict):
            return

        code: str = obj.get("code", "")
        name_ua: str = obj.get("name_ua", "")
        name_en: str | None = obj.get("name_en")
        children = obj.get("children")

        is_range = bool(code and "-" in code)  # e.g. "A00-A09"

        if code and not is_range:
            records.append({
                "code": code,
                "name_ua": name_ua,
                "name_en": name_en,
                "category": category,
            })

        new_category = code if is_range else category

        if isinstance(children, list):
            walk(children, new_category)
        elif isinstance(children, dict):
            for child in children.values():
                walk(child, new_category)

    # Top-level is a dict of class nodes (no code at this level)
    for class_node in data.get("children", {}).values():
        walk(class_node)

    return records


def import_icd10(file_path: str) -> None:
    source_path = Path(file_path)
    if not source_path.is_absolute():
        # Try relative to CWD and to this script's directory
        for candidate in [Path.cwd() / file_path, Path(__file__).parent / file_path]:
            if candidate.exists():
                source_path = candidate
                break

    if not source_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if source_path.suffix.lower() != ".json":
        raise ValueError(f"Expected .json file (mkh10.json format), got: {source_path.name}")

    print(f"Reading {source_path} ...")
    with open(source_path, encoding="utf-8") as f:
        data = json.load(f)

    records = extract_records(data)
    total = len(records)
    print(f"Extracted {total} ICD-10 codes from JSON tree.")

    engine = create_engine(settings.DATABASE_URL_SYNC)
    imported = 0
    skipped = 0
    batch_size = 500

    with Session(engine) as session:
        for i in range(0, total, batch_size):
            batch = records[i:i + batch_size]
            for rec in batch:
                if not rec["code"] or not rec["name_ua"]:
                    skipped += 1
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
            done = min(i + batch_size, total)
            print(f"  Processed {done} / {total} ...")

    print(f"Done. Imported: {imported}, skipped (empty): {skipped}.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_icd10.py <mkh10.json>")
        print("  Example: python scripts/import_icd10.py scripts/mkh10.json")
        sys.exit(1)

    try:
        import_icd10(sys.argv[1])
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)
