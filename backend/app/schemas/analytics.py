from __future__ import annotations

import enum
import uuid
from typing import Optional

from pydantic import BaseModel


class GroupBy(str, enum.Enum):
    day   = "day"
    week  = "week"
    month = "month"


# ─── 1. Appointments by period ────────────────────────────────────────────────

class AppointmentPeriodResponse(BaseModel):
    period: str
    total: int
    cancelled: int
    completed: int


# ─── 2. Top-10 ICD-10 diagnoses ──────────────────────────────────────────────

class TopDiagnosisResponse(BaseModel):
    icd10_code: str
    name_ua: str
    count: int


# ─── 3. Doctor load ───────────────────────────────────────────────────────────

class DoctorLoadResponse(BaseModel):
    doctor_id: uuid.UUID
    full_name: str
    specialization: Optional[str]
    encounters_count: int
    appointments_count: int


# ─── 4. Prescriptions by period ──────────────────────────────────────────────

class PrescriptionPeriodResponse(BaseModel):
    period: str
    total: int
    active: int
    cancelled: int


# ─── 5. Cancellation rate ─────────────────────────────────────────────────────

class CancellationRateResponse(BaseModel):
    total_appointments: int
    cancelled: int
    cancellation_rate: float
