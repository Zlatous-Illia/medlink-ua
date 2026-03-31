from __future__ import annotations

import asyncio
import functools
import io
import uuid
from datetime import datetime, timezone, date, timedelta
from typing import Optional

import redis.asyncio as aioredis
from fastapi import HTTPException
from jinja2 import Environment, FileSystemLoader
from minio import Minio
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.core.config import settings
from app.models.clinical import Encounter, Diagnosis, EncounterStatus
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.reference import ICD10Code
from app.models.scheduling import Appointment, AppointmentStatus
from app.models.user import AuditLog, User, UserRole
from app.schemas.encounters import (
    EncounterCreate, EncounterUpdate, EncounterResponse,
    DiagnosisCreate, DiagnosisResponse,
    AppointmentTodayResponse, ICD10SearchResponse,
)

import os

_minio_client: Optional[Minio] = None


def _get_minio() -> Minio:
    global _minio_client
    if _minio_client is None:
        _minio_client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_USE_SSL,
        )
    return _minio_client


async def _run_sync(func, *args, **kwargs):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, functools.partial(func, *args, **kwargs))


class EncounterService:

    def __init__(self, db: AsyncSession, redis: aioredis.Redis):
        self.db = db
        self.redis = redis

    async def _get_doctor_record(self, user: User) -> Doctor:
        result = await self.db.execute(
            select(Doctor).where(Doctor.user_id == user.id)
        )
        doctor = result.scalar_one_or_none()
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor profile not found")
        return doctor

    async def _load_encounter(self, encounter_id: uuid.UUID, doctor: Doctor) -> Encounter:
        result = await self.db.execute(
            select(Encounter)
            .where(Encounter.id == encounter_id)
            .options(selectinload(Encounter.diagnoses).selectinload(Diagnosis.icd10))
        )
        encounter = result.scalar_one_or_none()
        if not encounter:
            raise HTTPException(status_code=404, detail="Encounter not found")
        if encounter.doctor_id != doctor.id:
            raise HTTPException(status_code=403, detail="Access denied")
        return encounter

    async def get_today_appointments(self, doctor_user: User) -> list[AppointmentTodayResponse]:
        doctor = await self._get_doctor_record(doctor_user)
        today = date.today()
        start = datetime(today.year, today.month, today.day, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(today.year, today.month, today.day, 23, 59, 59, tzinfo=timezone.utc)

        result = await self.db.execute(
            select(Appointment)
            .where(
                and_(
                    Appointment.doctor_id == doctor.id,
                    Appointment.slot_datetime >= start,
                    Appointment.slot_datetime <= end,
                    Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]),
                )
            )
            .options(selectinload(Appointment.patient))
            .order_by(Appointment.slot_datetime.asc())
        )
        appointments = result.scalars().all()
        return [AppointmentTodayResponse.model_validate(a) for a in appointments]

    async def create_encounter(self, data: EncounterCreate, doctor_user: User) -> EncounterResponse:
        doctor = await self._get_doctor_record(doctor_user)

        appointment = None
        if data.appointment_id:
            apt_result = await self.db.execute(
                select(Appointment).where(Appointment.id == data.appointment_id)
            )
            appointment = apt_result.scalar_one_or_none()
            if not appointment:
                raise HTTPException(status_code=404, detail="Appointment not found")
            if appointment.doctor_id != doctor.id:
                raise HTTPException(status_code=403, detail="Appointment does not belong to this doctor")

        encounter = Encounter(
            patient_id=data.patient_id,
            doctor_id=doctor.id,
            appointment_id=data.appointment_id,
            status=EncounterStatus.IN_PROGRESS,
        )
        self.db.add(encounter)

        if appointment:
            appointment.status = AppointmentStatus.COMPLETED

        await self.db.flush()

        self.db.add(AuditLog(
            user_id=doctor_user.id, action="CREATE_ENCOUNTER",
            resource="encounters", resource_id=encounter.id,
        ))
        await self.db.commit()
        await self.db.refresh(encounter)
        return EncounterResponse(
            id=encounter.id,
            patient_id=encounter.patient_id,
            doctor_id=encounter.doctor_id,
            appointment_id=encounter.appointment_id,
            status=encounter.status,
            started_at=encounter.started_at,
            completed_at=encounter.completed_at,
            complaints=encounter.complaints,
            anamnesis=encounter.anamnesis,
            objective_exam=encounter.objective_exam,
            treatment_plan=encounter.treatment_plan,
            recommendations=encounter.recommendations,
            pdf_url=encounter.pdf_url,
            diagnoses=[],
        )

    async def get_encounter(self, encounter_id: uuid.UUID, doctor_user: User) -> EncounterResponse:
        doctor = await self._get_doctor_record(doctor_user)
        encounter = await self._load_encounter(encounter_id, doctor)
        return EncounterResponse.model_validate(encounter)

    async def update_encounter(self, encounter_id: uuid.UUID, data: EncounterUpdate, doctor_user: User) -> EncounterResponse:
        doctor = await self._get_doctor_record(doctor_user)
        encounter = await self._load_encounter(encounter_id, doctor)
        if encounter.status != EncounterStatus.IN_PROGRESS:
            raise HTTPException(status_code=400, detail="Encounter already completed")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(encounter, field, value)
        await self.db.commit()
        await self.db.refresh(encounter)
        # Re-load with diagnoses
        result = await self.db.execute(
            select(Encounter)
            .where(Encounter.id == encounter_id)
            .options(selectinload(Encounter.diagnoses).selectinload(Diagnosis.icd10))
        )
        encounter = result.scalar_one()
        return EncounterResponse.model_validate(encounter)

    async def complete_encounter(self, encounter_id: uuid.UUID, doctor_user: User) -> EncounterResponse:
        doctor = await self._get_doctor_record(doctor_user)
        encounter = await self._load_encounter(encounter_id, doctor)
        if encounter.status != EncounterStatus.IN_PROGRESS:
            raise HTTPException(status_code=400, detail="Encounter already completed")
        encounter.status = EncounterStatus.COMPLETED
        encounter.completed_at = datetime.now(timezone.utc)
        self.db.add(AuditLog(
            user_id=doctor_user.id, action="COMPLETE_ENCOUNTER",
            resource="encounters", resource_id=encounter.id,
        ))
        await self.db.commit()
        await self.db.refresh(encounter)
        result = await self.db.execute(
            select(Encounter)
            .where(Encounter.id == encounter_id)
            .options(selectinload(Encounter.diagnoses).selectinload(Diagnosis.icd10))
        )
        encounter = result.scalar_one()
        return EncounterResponse.model_validate(encounter)

    async def get_encounter_pdf(self, encounter_id: uuid.UUID, requesting_user: User) -> bytes:
        result = await self.db.execute(
            select(Encounter)
            .where(Encounter.id == encounter_id)
            .options(
                selectinload(Encounter.diagnoses).selectinload(Diagnosis.icd10),
                selectinload(Encounter.patient),
                joinedload(Encounter.doctor).joinedload(Doctor.user),
                joinedload(Encounter.doctor).joinedload(Doctor.specialization),
            )
        )
        encounter = result.scalar_one_or_none()
        if not encounter:
            raise HTTPException(status_code=404, detail="Encounter not found")

        # Check if PDF already exists in MinIO
        if encounter.pdf_url:
            minio = _get_minio()
            bucket = settings.MINIO_BUCKET_DOCUMENTS
            object_key = f"encounters/{encounter_id}/discharge.pdf"
            try:
                response = await _run_sync(minio.get_object, bucket, object_key)
                pdf_bytes = response.read()
                response.close()
                response.release_conn()
                self.db.add(AuditLog(
                    user_id=requesting_user.id, action="GENERATE_PDF",
                    resource="encounters", resource_id=encounter_id,
                ))
                await self.db.commit()
                return pdf_bytes
            except Exception:
                pass

        # Generate PDF via Jinja2 + WeasyPrint
        templates_dir = os.path.join(os.path.dirname(__file__), "..", "..", "templates")
        templates_dir = os.path.abspath(templates_dir)
        env = Environment(loader=FileSystemLoader(templates_dir))
        template = env.get_template("encounter_pdf.html")

        html_content = template.render(
            encounter=encounter,
            patient=encounter.patient,
            doctor=encounter.doctor,
        )

        from weasyprint import HTML
        pdf_bytes = await _run_sync(lambda: HTML(string=html_content).write_pdf())

        # Save to MinIO
        minio = _get_minio()
        bucket = settings.MINIO_BUCKET_DOCUMENTS
        object_key = f"encounters/{encounter_id}/discharge.pdf"

        await _run_sync(
            minio.put_object,
            bucket,
            object_key,
            io.BytesIO(pdf_bytes),
            len(pdf_bytes),
            content_type="application/pdf",
        )

        protocol = "https" if settings.MINIO_USE_SSL else "http"
        encounter.pdf_url = f"{protocol}://{settings.MINIO_ENDPOINT}/{bucket}/{object_key}"

        self.db.add(AuditLog(
            user_id=requesting_user.id, action="GENERATE_PDF",
            resource="encounters", resource_id=encounter_id,
        ))
        await self.db.commit()
        return pdf_bytes

    async def get_patient_encounters(self, patient_id: uuid.UUID) -> list[EncounterResponse]:
        result = await self.db.execute(
            select(Encounter)
            .where(Encounter.patient_id == patient_id)
            .options(selectinload(Encounter.diagnoses).selectinload(Diagnosis.icd10))
            .order_by(Encounter.started_at.desc())
        )
        encounters = result.scalars().all()
        return [EncounterResponse.model_validate(e) for e in encounters]

    async def add_diagnosis(self, encounter_id: uuid.UUID, data: DiagnosisCreate, doctor_user: User) -> DiagnosisResponse:
        doctor = await self._get_doctor_record(doctor_user)
        encounter = await self._load_encounter(encounter_id, doctor)
        if encounter.status != EncounterStatus.IN_PROGRESS:
            raise HTTPException(status_code=400, detail="Encounter already completed")

        diagnosis = Diagnosis(
            encounter_id=encounter_id,
            icd10_id=data.icd10_id,
            type=data.type,
            notes=data.notes,
        )
        self.db.add(diagnosis)
        await self.db.flush()

        result = await self.db.execute(
            select(Diagnosis)
            .where(Diagnosis.id == diagnosis.id)
            .options(selectinload(Diagnosis.icd10))
        )
        diagnosis = result.scalar_one()
        await self.db.commit()
        return DiagnosisResponse.model_validate(diagnosis)

    async def search_icd10(self, query: str, limit: int = 20) -> list[ICD10SearchResponse]:
        limit = min(limit, 50)
        pattern = f"%{query}%"
        result = await self.db.execute(
            select(ICD10Code)
            .where(
                and_(
                    ICD10Code.is_active == True,
                    (ICD10Code.code.ilike(pattern) | ICD10Code.name_ua.ilike(pattern)),
                )
            )
            .limit(limit)
        )
        codes = result.scalars().all()
        return [ICD10SearchResponse.model_validate(c) for c in codes]
