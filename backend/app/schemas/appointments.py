from __future__ import annotations

import uuid
from datetime import datetime, date, time
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.scheduling import AppointmentStatus
from app.schemas.patients import PatientResponse


class SpecializationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name_ua: str
    name_en: Optional[str] = None
    code: Optional[str] = None


class DoctorListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    specialization: Optional[SpecializationResponse] = None
    license_number: Optional[str] = None
    experience_years: Optional[int] = None
    bio: Optional[str] = None
    photo_url: Optional[str] = None
    full_name: str


class SlotResponse(BaseModel):
    slot_datetime: datetime
    duration_min: int
    is_available: bool


class ScheduleCreate(BaseModel):
    day_of_week: int  # 0-6
    start_time: time
    end_time: time
    slot_duration: int = 20


class ScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    doctor_id: uuid.UUID
    day_of_week: int
    start_time: time
    end_time: time
    slot_duration: int
    is_active: bool


class AppointmentCreate(BaseModel):
    doctor_id: uuid.UUID
    slot_datetime: datetime
    reason: Optional[str] = None


class AppointmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    doctor_id: uuid.UUID
    slot_datetime: datetime
    duration_min: int
    reason: Optional[str] = None
    status: AppointmentStatus
    cancel_reason: Optional[str] = None
    created_at: datetime
    doctor: Optional[DoctorListResponse] = None
    patient: Optional[PatientResponse] = None


class AppointmentCancelRequest(BaseModel):
    reason: Optional[str] = None
