from __future__ import annotations

import asyncio
import functools
import io
import uuid
from typing import Optional

import redis.asyncio as aioredis
from fastapi import HTTPException, UploadFile
from minio import Minio
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.security import verify_password, hash_password
from app.models.clinical import (
    Encounter, Diagnosis, Prescription, PrescriptionStatus,
)
from app.models.doctor import Doctor
from app.models.patient import (
    Patient, MedicalCard, Allergy, ChronicDisease, PatientDocument,
)
from app.models.user import User, AuditLog, RefreshToken
from app.schemas.patient_cabinet import (
    UserProfileResponse, ProfileUpdate,
    MedicalCardReadResponse, AllergyReadResponse, ChronicDiseaseReadResponse, ICD10Brief,
    MyEncounterResponse, DiagnosisBriefResponse,
    MyPrescriptionResponse, DrugBriefResponse,
    MyDocumentResponse,
)


# ─── MinIO helpers ────────────────────────────────────────────────────────────

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


# ─── Service ──────────────────────────────────────────────────────────────────

class PatientCabinetService:

    def __init__(self, db: AsyncSession, redis: aioredis.Redis):
        self.db = db
        self.redis = redis

    # ── GET /me ───────────────────────────────────────────────────────────────

    async def get_profile(self, user: User) -> UserProfileResponse:
        # Find linked patient_id if exists
        result = await self.db.execute(
            select(Patient.id).where(Patient.user_id == user.id)
        )
        patient_id = result.scalar_one_or_none()

        self.db.add(AuditLog(
            user_id=user.id, action="VIEW_PROFILE",
            resource="users", resource_id=user.id,
        ))
        await self.db.commit()

        return UserProfileResponse(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            middle_name=user.middle_name,
            phone=user.phone,
            avatar_url=user.avatar_url,
            role=user.role,
            patient_id=patient_id,
            created_at=user.created_at,
        )

    # ── PATCH /me ─────────────────────────────────────────────────────────────

    async def update_profile(self, user: User, data: ProfileUpdate) -> UserProfileResponse:
        updates = data.model_dump(exclude_unset=True)
        if not updates:
            return await self.get_profile(user)

        for field, value in updates.items():
            setattr(user, field, value)

        self.db.add(AuditLog(
            user_id=user.id, action="UPDATE_PROFILE",
            resource="users", resource_id=user.id,
            details=updates,
        ))
        await self.db.commit()
        await self.db.refresh(user)
        return await self.get_profile(user)

    # ── POST /me/avatar ───────────────────────────────────────────────────────

    async def upload_avatar(self, user: User, file: UploadFile) -> UserProfileResponse:
        allowed_types = {"image/jpeg", "image/png"}
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Allowed: image/jpeg, image/png",
            )

        content = await file.read()
        if len(content) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File size exceeds 5 MB limit")

        bucket = settings.MINIO_BUCKET_AVATARS
        object_key = f"avatars/{user.id}/{uuid.uuid4()}_{file.filename}"
        minio = _get_minio()

        # Delete old avatar if exists
        if user.avatar_url:
            try:
                prefix = f"/{bucket}/"
                if prefix in user.avatar_url:
                    old_key = user.avatar_url.split(prefix, 1)[1]
                    await _run_sync(minio.remove_object, bucket, old_key)
            except Exception:
                pass  # ignore errors on old avatar removal

        await _run_sync(
            minio.put_object,
            bucket,
            object_key,
            io.BytesIO(content),
            len(content),
            content_type=file.content_type,
        )

        protocol = "https" if settings.MINIO_USE_SSL else "http"
        user.avatar_url = f"{protocol}://{settings.MINIO_ENDPOINT}/{bucket}/{object_key}"

        self.db.add(AuditLog(
            user_id=user.id, action="UPLOAD_AVATAR",
            resource="users", resource_id=user.id,
        ))
        await self.db.commit()
        await self.db.refresh(user)
        return await self.get_profile(user)

    # ── GET /me/medical-card ──────────────────────────────────────────────────

    async def get_medical_card(self, user: User) -> MedicalCardReadResponse:
        result = await self.db.execute(
            select(Patient)
            .where(Patient.user_id == user.id, Patient.is_active == True)
            .options(
                selectinload(Patient.medical_card),
                selectinload(Patient.allergies),
                selectinload(Patient.chronic_diseases).selectinload(ChronicDisease.icd10),
            )
        )
        patient = result.scalar_one_or_none()
        if not patient:
            raise HTTPException(
                status_code=404,
                detail="Профіль пацієнта не підключено до акаунту",
            )
        if not patient.medical_card:
            raise HTTPException(status_code=404, detail="Медична картка не знайдена")

        self.db.add(AuditLog(
            user_id=user.id, action="VIEW_MEDICAL_CARD",
            resource="medical_cards", resource_id=patient.medical_card.id,
        ))
        await self.db.commit()

        card = patient.medical_card
        return MedicalCardReadResponse(
            id=card.id,
            patient_id=card.patient_id,
            blood_type=card.blood_type,
            height_cm=card.height_cm,
            weight_kg=float(card.weight_kg) if card.weight_kg is not None else None,
            smoking_status=card.smoking_status,
            notes=card.notes,
            allergies=[AllergyReadResponse.model_validate(a) for a in patient.allergies],
            chronic_diseases=[
                ChronicDiseaseReadResponse(
                    id=cd.id,
                    diagnosed_at=cd.diagnosed_at,
                    notes=cd.notes,
                    icd10=ICD10Brief(code=cd.icd10.code, name_ua=cd.icd10.name_ua),
                )
                for cd in patient.chronic_diseases
            ],
        )

    # ── GET /me/encounters ────────────────────────────────────────────────────

    async def get_encounters(self, user: User) -> list[MyEncounterResponse]:
        patient = await self._get_patient(user)

        result = await self.db.execute(
            select(Encounter)
            .where(Encounter.patient_id == patient.id)
            .options(
                selectinload(Encounter.doctor).selectinload(Doctor.user),
                selectinload(Encounter.diagnoses).selectinload(Diagnosis.icd10),
            )
            .order_by(Encounter.started_at.desc())
        )
        encounters = result.scalars().all()

        self.db.add(AuditLog(
            user_id=user.id, action="VIEW_ENCOUNTERS",
            resource="patients", resource_id=patient.id,
        ))
        await self.db.commit()

        responses = []
        for enc in encounters:
            diagnoses = [
                DiagnosisBriefResponse(
                    code=d.icd10.code,
                    name_ua=d.icd10.name_ua,
                    type=d.type,
                )
                for d in enc.diagnoses
                if d.icd10
            ]
            doctor_name = enc.doctor.full_name if enc.doctor else ""
            responses.append(MyEncounterResponse(
                id=enc.id,
                started_at=enc.started_at,
                completed_at=enc.completed_at,
                status=enc.status,
                doctor_full_name=doctor_name,
                diagnoses=diagnoses,
                pdf_url=enc.pdf_url,
            ))
        return responses

    # ── GET /me/prescriptions ─────────────────────────────────────────────────

    async def get_prescriptions(
        self, user: User, status: Optional[PrescriptionStatus] = None
    ) -> list[MyPrescriptionResponse]:
        patient = await self._get_patient(user)

        query = (
            select(Prescription)
            .where(Prescription.patient_id == patient.id)
            .options(selectinload(Prescription.drug))
            .order_by(Prescription.created_at.desc())
        )
        if status:
            query = query.where(Prescription.status == status)

        result = await self.db.execute(query)
        prescriptions = result.scalars().all()

        self.db.add(AuditLog(
            user_id=user.id, action="VIEW_PRESCRIPTIONS",
            resource="patients", resource_id=patient.id,
        ))
        await self.db.commit()

        return [
            MyPrescriptionResponse(
                id=p.id,
                drug=DrugBriefResponse.model_validate(p.drug),
                dosage=p.dosage,
                frequency=p.frequency,
                duration_days=p.duration_days,
                instructions=p.instructions,
                status=p.status,
                esoz_request_number=p.esoz_request_number,
                created_at=p.created_at,
                expires_at=p.expires_at,
            )
            for p in prescriptions
        ]

    # ── GET /me/documents ─────────────────────────────────────────────────────

    async def get_documents(self, user: User) -> list[MyDocumentResponse]:
        patient = await self._get_patient(user)

        result = await self.db.execute(
            select(PatientDocument)
            .where(PatientDocument.patient_id == patient.id)
            .order_by(PatientDocument.created_at.desc())
        )
        documents = result.scalars().all()

        return [
            MyDocumentResponse(
                id=doc.id,
                file_name=doc.file_name,
                file_type=doc.file_type,
                file_url=doc.file_url,
                file_size=doc.file_size,
                uploaded_at=doc.created_at,
            )
            for doc in documents
        ]

    # ── PATCH /me/change-password ─────────────────────────────────────────────

    async def change_password(
        self, user: User, current_password: str, new_password: str
    ) -> dict:
        if not verify_password(current_password, user.password_hash):
            raise HTTPException(status_code=400, detail="Поточний пароль невірний")

        user.password_hash = hash_password(new_password)

        # Revoke all refresh tokens
        await self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user.id)
            .values(is_revoked=True)
        )

        self.db.add(AuditLog(
            user_id=user.id, action="CHANGE_PASSWORD",
            resource="users", resource_id=user.id,
        ))
        await self.db.commit()
        return {"message": "Пароль успішно змінено"}

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _get_patient(self, user: User) -> Patient:
        result = await self.db.execute(
            select(Patient).where(Patient.user_id == user.id, Patient.is_active == True)
        )
        patient = result.scalar_one_or_none()
        if not patient:
            raise HTTPException(
                status_code=404,
                detail="Профіль пацієнта не підключено до акаунту",
            )
        return patient
