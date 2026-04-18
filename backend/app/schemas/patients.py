from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.patient import Gender, BloodType, AllergySeverity


# ─── Patient ─────────────────────────────────────────────────────────────────

class PatientCreate(BaseModel):
    tax_id: str
    unzr: Optional[str] = None
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    birth_date: date
    gender: Gender
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[dict] = None
    primary_doctor_id: Optional[uuid.UUID] = None
    user_email: Optional[str] = None  # link to existing User account


class PatientUpdate(BaseModel):
    unzr: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    birth_date: Optional[date] = None
    gender: Optional[Gender] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[dict] = None
    primary_doctor_id: Optional[uuid.UUID] = None


class PatientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    tax_id: str
    unzr: Optional[str] = None
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    birth_date: date
    gender: Gender
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[dict] = None
    primary_doctor_id: Optional[uuid.UUID] = None
    esoz_person_id: Optional[uuid.UUID] = None
    is_active: bool
    created_at: datetime


# ─── Allergy ─────────────────────────────────────────────────────────────────

class AllergyCreate(BaseModel):
    substance: str
    severity: AllergySeverity
    reaction: Optional[str] = None


class AllergyUpdate(BaseModel):
    substance: Optional[str] = None
    severity: Optional[AllergySeverity] = None
    reaction: Optional[str] = None


class AllergyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    substance: str
    severity: AllergySeverity
    reaction: Optional[str] = None
    created_at: datetime


# ─── Chronic Disease ──────────────────────────────────────────────────────────

class ChronicDiseaseCreate(BaseModel):
    icd10_id: uuid.UUID
    diagnosed_at: Optional[date] = None
    notes: Optional[str] = None


class ChronicDiseaseUpdate(BaseModel):
    diagnosed_at: Optional[date] = None
    notes: Optional[str] = None


class ICD10Summary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name_ua: str


class ChronicDiseaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    icd10_id: uuid.UUID
    diagnosed_at: Optional[date] = None
    notes: Optional[str] = None
    icd10: Optional[ICD10Summary] = None
    created_at: datetime


# ─── Medical Card ─────────────────────────────────────────────────────────────

class MedicalCardUpdate(BaseModel):
    blood_type: Optional[BloodType] = None
    height_cm: Optional[int] = None
    weight_kg: Optional[float] = None
    disability_group: Optional[str] = None
    notes: Optional[str] = None


class MedicalCardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    blood_type: Optional[BloodType] = None
    height_cm: Optional[int] = None
    weight_kg: Optional[float] = None
    disability_group: Optional[str] = None
    notes: Optional[str] = None
    allergies: list[AllergyResponse] = []
    chronic_diseases: list[ChronicDiseaseResponse] = []


# ─── Document ────────────────────────────────────────────────────────────────

class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    file_name: str
    file_url: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    created_at: datetime


# ─── History (Encounter summary) ─────────────────────────────────────────────

class DiagnosisSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    icd10_id: uuid.UUID
    type: str
    notes: Optional[str] = None


class EncounterSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    doctor_id: uuid.UUID
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    complaints: Optional[str] = None
    diagnoses: list[DiagnosisSummary] = []


# ─── Allergen (reference table) ───────────────────────────────────────────────

class AllergenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name_ua: str
    category: Optional[str] = None
    international_name: Optional[str] = None