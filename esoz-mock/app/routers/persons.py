import uuid
from typing import Optional
from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel

# ─── Persons ─────────────────────────────────────────────────────────────────
router = APIRouter(tags=["Persons (Пацієнти ЕСОЗ)"])

_mock_persons = {
    "1234567890": {"id": str(uuid.uuid4()), "tax_id": "1234567890", "first_name": "Тестовий", "last_name": "Пацієнт", "verification_status": "VERIFIED"},
    "0987654321": {"id": str(uuid.uuid4()), "tax_id": "0987654321", "first_name": "Марія",    "last_name": "Іваненко",  "verification_status": "VERIFIED"},
}


def _require_auth(authorization: Optional[str]):
    if not authorization or not authorization.startswith("Bearer mock_esoz_token_"):
        raise HTTPException(status_code=401, detail="Invalid or missing ЕСОЗ token")


@router.get("/persons")
async def search_persons(
    tax_id: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
):
    """Пошук пацієнта за РНОКПП."""
    _require_auth(authorization)
    if tax_id and tax_id in _mock_persons:
        return {"data": [_mock_persons[tax_id]]}
    # Return mock unverified person for unknown tax_id
    return {"data": [{"id": str(uuid.uuid4()), "tax_id": tax_id, "verification_status": "NOT_VERIFIED"}]}


@router.get("/persons/{person_id}")
async def get_person(
    person_id: str,
    authorization: Optional[str] = Header(None),
):
    """Отримання даних пацієнта з ЕСОЗ за ID."""
    _require_auth(authorization)
    for p in _mock_persons.values():
        if p["id"] == person_id:
            return {"data": p}
    raise HTTPException(status_code=404, detail="Person not found in ЕСОЗ")
