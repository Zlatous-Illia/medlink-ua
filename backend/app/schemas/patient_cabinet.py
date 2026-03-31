from __future__ import annotations

import uuid
from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.patient import BloodType, SmokingStatus, AllergySeverity
from app.models.clinical import EncounterStatus, DiagnosisType, PrescriptionStatus
from app.models.user import UserRole


# ─── Profile ──────────────────────────────────────────────────────────────────

class UserProfileResponse(BaseModel):
    id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    middle_name: Optional[str]
    phone: Optional[str]
    avatar_url: Optional[str]
    role: UserRole
    patient_id: Optional[uuid.UUID]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    phone: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


# ─── Medical Card (read-only) ─────────────────────────────────────────────────

class AllergyReadResponse(BaseModel):
    id: uuid.UUID
    substance: str
    severity: AllergySeverity
    reaction: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ICD10Brief(BaseModel):
    code: str
    name_ua: str
    model_config = ConfigDict(from_attributes=True)


class ChronicDiseaseReadResponse(BaseModel):
    id: uuid.UUID
    diagnosed_at: Optional[date]
    notes: Optional[str]
    icd10: ICD10Brief
    model_config = ConfigDict(from_attributes=True)


class MedicalCardReadResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    blood_type: Optional[BloodType]
    height_cm: Optional[int]
    weight_kg: Optional[float]
    smoking_status: SmokingStatus
    notes: Optional[str]
    allergies: list[AllergyReadResponse]
    chronic_diseases: list[ChronicDiseaseReadResponse]
    model_config = ConfigDict(from_attributes=True)


# ─── Encounters ───────────────────────────────────────────────────────────────

class DiagnosisBriefResponse(BaseModel):
    code: str
    name_ua: str
    type: DiagnosisType


class MyEncounterResponse(BaseModel):
    id: uuid.UUID
    started_at: datetime
    completed_at: Optional[datetime]
    status: EncounterStatus
    doctor_full_name: str
    diagnoses: list[DiagnosisBriefResponse]
    pdf_url: Optional[str]


# ─── Prescriptions ────────────────────────────────────────────────────────────

class DrugBriefResponse(BaseModel):
    id: uuid.UUID
    inn: str
    trade_name: Optional[str]
    form: Optional[str]
    dosage: Optional[str]
    model_config = ConfigDict(from_attributes=True)


class MyPrescriptionResponse(BaseModel):
    id: uuid.UUID
    drug: DrugBriefResponse
    dosage: Optional[str]
    frequency: Optional[str]
    duration_days: Optional[int]
    instructions: Optional[str]
    status: PrescriptionStatus
    esoz_request_number: Optional[str]
    created_at: datetime
    expires_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)


# ─── Documents ────────────────────────────────────────────────────────────────

class MyDocumentResponse(BaseModel):
    id: uuid.UUID
    file_name: str
    file_type: Optional[str]
    file_url: str
    file_size: Optional[int]
    uploaded_at: datetime
