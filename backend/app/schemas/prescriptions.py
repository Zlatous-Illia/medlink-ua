from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.clinical import PrescriptionStatus


class DrugResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    atc_code: Optional[str] = None
    inn: str
    trade_name: Optional[str] = None
    form: Optional[str] = None
    dosage: Optional[str] = None


class PrescriptionCreate(BaseModel):
    encounter_id: uuid.UUID
    drug_id: uuid.UUID
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    duration_days: Optional[int] = None
    quantity: Optional[int] = None
    instructions: Optional[str] = None


class PrescriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    encounter_id: uuid.UUID
    patient_id: uuid.UUID
    doctor_id: uuid.UUID
    drug_id: uuid.UUID
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    duration_days: Optional[int] = None
    quantity: Optional[int] = None
    instructions: Optional[str] = None
    status: PrescriptionStatus
    esoz_request_id: Optional[uuid.UUID] = None
    esoz_request_number: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    drug: Optional[DrugResponse] = None


class PrescriptionCancelRequest(BaseModel):
    reason: str
