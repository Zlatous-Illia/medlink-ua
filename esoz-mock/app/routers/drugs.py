import uuid
from typing import Optional
from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel

# ─── Drugs ───────────────────────────────────────────────────────────────────
router = APIRouter(tags=["Drugs & Referrals"])

MOCK_DRUGS = [
    {"id": str(uuid.uuid4()), "atc_code": "J01CA04", "inn": "Амоксицилін",    "form": "таблетки",  "dosage": "500 мг"},
    {"id": str(uuid.uuid4()), "atc_code": "J01FA09", "inn": "Кларитроміцин",  "form": "таблетки",  "dosage": "500 мг"},
    {"id": str(uuid.uuid4()), "atc_code": "N02BE01", "inn": "Парацетамол",     "form": "таблетки",  "dosage": "500 мг"},
    {"id": str(uuid.uuid4()), "atc_code": "M01AE01", "inn": "Ібупрофен",       "form": "таблетки",  "dosage": "400 мг"},
    {"id": str(uuid.uuid4()), "atc_code": "C09AA05", "inn": "Раміприл",        "form": "таблетки",  "dosage": "5 мг"},
    {"id": str(uuid.uuid4()), "atc_code": "C10AA01", "inn": "Симвастатин",     "form": "таблетки",  "dosage": "20 мг"},
    {"id": str(uuid.uuid4()), "atc_code": "A02BC01", "inn": "Омепразол",       "form": "капсули",   "dosage": "20 мг"},
    {"id": str(uuid.uuid4()), "atc_code": "R03AC02", "inn": "Сальбутамол",     "form": "інгалятор", "dosage": "100 мкг/доза"},
    {"id": str(uuid.uuid4()), "atc_code": "B01AC06", "inn": "Ацетилсаліцилова кислота", "form": "таблетки", "dosage": "100 мг"},
    {"id": str(uuid.uuid4()), "atc_code": "A10BB01", "inn": "Глібенкламід",    "form": "таблетки",  "dosage": "5 мг"},
]


def _require_auth(authorization: Optional[str]):
    if not authorization or not authorization.startswith("Bearer mock_esoz_token_"):
        raise HTTPException(status_code=401, detail="Invalid or missing ЕСОЗ token")


@router.get("/innm_dosages")
async def get_drugs(
    name: Optional[str] = Query(None, description="Пошук за МНН або торговою назвою"),
    page_size: int = Query(20, le=100),
    authorization: Optional[str] = Header(None),
):
    """Довідник лікарських засобів (АТХ/МНН) з ЕСОЗ."""
    _require_auth(authorization)
    results = MOCK_DRUGS
    if name:
        name_lower = name.lower()
        results = [d for d in MOCK_DRUGS if name_lower in d["inn"].lower()]
    return {"data": results[:page_size], "total": len(results)}


# ─── Referrals ────────────────────────────────────────────────────────────────

_referrals: dict[str, dict] = {}


class ReferralRequest(BaseModel):
    patient_id: str
    doctor_id: str
    specialization_code: Optional[str] = None
    reason: Optional[str] = None


@router.post("/referrals")
async def create_referral(
    data: ReferralRequest,
    authorization: Optional[str] = Header(None),
):
    """Створення е-направлення в ЕСОЗ."""
    _require_auth(authorization)
    ref_id = str(uuid.uuid4())
    record = {
        "id": ref_id,
        "status": "active",
        "patient_id": data.patient_id,
        "doctor_id": data.doctor_id,
        "specialization_code": data.specialization_code,
        "reason": data.reason,
    }
    _referrals[ref_id] = record
    return {"data": record}


@router.get("/referrals/{referral_id}")
async def get_referral(
    referral_id: str,
    authorization: Optional[str] = Header(None),
):
    _require_auth(authorization)
    record = _referrals.get(referral_id)
    if not record:
        raise HTTPException(status_code=404, detail="Referral not found")
    return {"data": record}
