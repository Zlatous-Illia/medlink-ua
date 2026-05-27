from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.clinical import DiagnosisType, EncounterStatus, ReferralStatus
from app.models.scheduling import AppointmentStatus
from app.schemas.patients import PatientResponse, ICD10Summary


class DiagnosisCreate(BaseModel):
    icd10_id: uuid.UUID
    type: DiagnosisType = DiagnosisType.MAIN
    notes: Optional[str] = None


class DiagnosisUpdate(BaseModel):
    icd10_id: Optional[uuid.UUID] = None
    type: Optional[DiagnosisType] = None
    notes: Optional[str] = None


class DiagnosisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    encounter_id: uuid.UUID
    icd10_id: uuid.UUID
    type: DiagnosisType
    notes: Optional[str] = None
    icd10: Optional[ICD10Summary] = None


class EncounterCreate(BaseModel):
    patient_id: uuid.UUID
    appointment_id: Optional[uuid.UUID] = None


class EncounterUpdate(BaseModel):
    complaints: Optional[str] = None
    anamnesis: Optional[str] = None
    objective_exam: Optional[str] = None
    treatment_plan: Optional[str] = None
    recommendations: Optional[str] = None


class EncounterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    doctor_id: uuid.UUID
    appointment_id: Optional[uuid.UUID] = None
    status: EncounterStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    complaints: Optional[str] = None
    anamnesis: Optional[str] = None
    objective_exam: Optional[str] = None
    treatment_plan: Optional[str] = None
    recommendations: Optional[str] = None
    pdf_url: Optional[str] = None
    diagnoses: list[DiagnosisResponse] = []


class AppointmentTodayResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    slot_datetime: datetime
    duration_min: int
    reason: Optional[str] = None
    status: AppointmentStatus
    patient: Optional[PatientResponse] = None


class ReferralCreate(BaseModel):
    encounter_id: uuid.UUID
    specialization_id: Optional[uuid.UUID] = None
    reason: Optional[str] = None


class ReferralUpdate(BaseModel):
    encounter_id: Optional[uuid.UUID] = None
    specialization_id: Optional[uuid.UUID] = None
    reason: Optional[str] = None


class ReferralResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    encounter_id: uuid.UUID
    patient_id: uuid.UUID
    doctor_id: uuid.UUID
    specialization_id: Optional[uuid.UUID] = None
    reason: Optional[str] = None
    status: ReferralStatus
    esoz_referral_id: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None


class ICD10SearchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name_ua: str
    name_en: Optional[str] = None
    category: Optional[str] = None
