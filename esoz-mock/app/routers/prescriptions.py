import uuid
import random
import string
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["Medication Requests (Е-рецепти)"])

# In-memory store for demo
_prescriptions: dict[str, dict] = {}


def _require_auth(authorization: Optional[str]):
    if not authorization or not authorization.startswith("Bearer mock_esoz_token_"):
        raise HTTPException(status_code=401, detail="Invalid or missing ЕСОЗ token")


def _generate_request_number() -> str:
    """Генерує номер рецепту у форматі ЕСОЗ: 0000-XXXX-XXXX-XXXX"""
    parts = ["0000"] + [
        "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
        for _ in range(3)
    ]
    return "-".join(parts)


class PrescriptionRequest(BaseModel):
    patient_id: str
    doctor_id: str
    drug_inn: str
    drug_atc_code: Optional[str] = None
    dosage: str
    frequency: str
    duration_days: int
    quantity: int
    instructions: Optional[str] = None


@router.post("/medication_requests")
async def create_prescription(
    data: PrescriptionRequest,
    authorization: Optional[str] = Header(None),
):
    """Створення е-рецепту в ЕСОЗ."""
    _require_auth(authorization)

    rx_id = str(uuid.uuid4())
    rx_number = _generate_request_number()
    now = datetime.now(timezone.utc)

    record = {
        "id": rx_id,
        "request_number": rx_number,
        "status": "active",
        "patient_id": data.patient_id,
        "doctor_id": data.doctor_id,
        "drug_inn": data.drug_inn,
        "dosage": data.dosage,
        "frequency": data.frequency,
        "duration_days": data.duration_days,
        "quantity": data.quantity,
        "instructions": data.instructions,
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(days=30)).isoformat(),
    }
    _prescriptions[rx_id] = record

    return {"data": record}


@router.get("/medication_requests/{request_id}")
async def get_prescription(
    request_id: str,
    authorization: Optional[str] = Header(None),
):
    """Отримання статусу е-рецепту."""
    _require_auth(authorization)
    record = _prescriptions.get(request_id)
    if not record:
        raise HTTPException(status_code=404, detail="Prescription not found")
    return {"data": record}


@router.patch("/medication_requests/{request_id}")
async def update_prescription(
    request_id: str,
    payload: dict,
    authorization: Optional[str] = Header(None),
):
    """Оновлення статусу е-рецепту (скасування)."""
    _require_auth(authorization)
    record = _prescriptions.get(request_id)
    if not record:
        raise HTTPException(status_code=404, detail="Prescription not found")
    record.update(payload)
    return {"data": record}
