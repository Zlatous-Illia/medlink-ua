from __future__ import annotations

import asyncio
import functools
import io
import uuid
from typing import Optional

import redis.asyncio as aioredis
from fastapi import HTTPException, UploadFile
from minio import Minio
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.clinical import Encounter
from app.models.patient import (
    Patient, MedicalCard, Allergy, ChronicDisease, PatientDocument,
)
from app.models.user import AuditLog, User
from app.schemas.patients import (
    PatientCreate, PatientUpdate, PatientResponse,
    AllergyCreate, AllergyResponse,
    ChronicDiseaseCreate, ChronicDiseaseResponse,
    MedicalCardUpdate, MedicalCardResponse,
    DocumentResponse, EncounterSummary,
)

# ─── MinIO client (module-level singleton) ────────────────────────────────────

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

class PatientService:

    def __init__(self, db: AsyncSession, redis: aioredis.Redis):
        self.db = db
        self.redis = redis

    # ── Create patient ────────────────────────────────────────────────────────

    async def create_patient(
        self, data: PatientCreate, created_by_user_id: uuid.UUID
    ) -> PatientResponse:
        existing = await self.db.execute(
            select(Patient).where(Patient.tax_id == data.tax_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Patient with this tax_id already exists")

        patient = Patient(**data.model_dump(), created_by=created_by_user_id)
        self.db.add(patient)
        await self.db.flush()

        self.db.add(MedicalCard(patient_id=patient.id))
        self.db.add(AuditLog(
            user_id=created_by_user_id, action="CREATE_PATIENT",
            resource="patients", resource_id=patient.id,
        ))
        await self.db.commit()
        await self.db.refresh(patient)
        return PatientResponse.model_validate(patient)

    # ── List patients ─────────────────────────────────────────────────────────

    async def get_patients(
        self, search: Optional[str], skip: int, limit: int
    ) -> list[PatientResponse]:
        query = select(Patient).where(Patient.is_active == True)
        if search:
            pattern = f"%{search}%"
            query = query.where(
                or_(
                    Patient.first_name.ilike(pattern),
                    Patient.last_name.ilike(pattern),
                    Patient.tax_id.ilike(pattern),
                    Patient.phone.ilike(pattern),
                )
            )
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        patients = result.scalars().all()
        return [PatientResponse.model_validate(p) for p in patients]

    # ── Get single patient ────────────────────────────────────────────────────

    async def get_patient(
        self, patient_id: uuid.UUID, requesting_user: User
    ) -> PatientResponse:
        patient = await self._load_patient(patient_id)

        from app.models.user import UserRole
        if requesting_user.role == UserRole.PATIENT:
            if patient.user_id != requesting_user.id:
                raise HTTPException(status_code=403, detail="Access denied")

        self.db.add(AuditLog(
            user_id=requesting_user.id, action="VIEW_PATIENT",
            resource="patients", resource_id=patient_id,
        ))
        await self.db.commit()
        return PatientResponse.model_validate(patient)

    # ── Update patient ────────────────────────────────────────────────────────

    async def update_patient(
        self, patient_id: uuid.UUID, data: PatientUpdate, updated_by: User
    ) -> PatientResponse:
        patient = await self._load_patient(patient_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(patient, field, value)
        await self.db.commit()
        await self.db.refresh(patient)
        return PatientResponse.model_validate(patient)

    # ── Medical card ──────────────────────────────────────────────────────────

    async def get_medical_card(
        self, patient_id: uuid.UUID, requesting_user: User
    ) -> MedicalCardResponse:
        result = await self.db.execute(
            select(Patient)
            .where(Patient.id == patient_id, Patient.is_active == True)
            .options(
                selectinload(Patient.medical_card),
                selectinload(Patient.allergies),
                selectinload(Patient.chronic_diseases).selectinload(ChronicDisease.icd10),
            )
        )
        patient = result.scalar_one_or_none()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        if not patient.medical_card:
            raise HTTPException(status_code=404, detail="Medical card not found")

        self.db.add(AuditLog(
            user_id=requesting_user.id, action="VIEW_EMR",
            resource="medical_cards", resource_id=patient.medical_card.id,
        ))
        await self.db.commit()

        card = patient.medical_card
        return MedicalCardResponse(
            id=card.id,
            patient_id=card.patient_id,
            blood_type=card.blood_type,
            height_cm=card.height_cm,
            weight_kg=float(card.weight_kg) if card.weight_kg is not None else None,
            smoking_status=card.smoking_status,
            alcohol_status=card.alcohol_status,
            disability_group=card.disability_group,
            notes=card.notes,
            allergies=[AllergyResponse.model_validate(a) for a in patient.allergies],
            chronic_diseases=[
                ChronicDiseaseResponse.model_validate(cd) for cd in patient.chronic_diseases
            ],
        )

    async def update_medical_card(
        self, patient_id: uuid.UUID, data: MedicalCardUpdate, updated_by: User
    ) -> MedicalCardResponse:
        result = await self.db.execute(
            select(MedicalCard).where(MedicalCard.patient_id == patient_id)
        )
        card = result.scalar_one_or_none()
        if not card:
            raise HTTPException(status_code=404, detail="Medical card not found")

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(card, field, value)
        card.updated_by = updated_by.id

        self.db.add(AuditLog(
            user_id=updated_by.id, action="UPDATE_EMR",
            resource="medical_cards", resource_id=card.id,
        ))
        await self.db.commit()

        return await self.get_medical_card(patient_id, updated_by)

    # ── Allergies ─────────────────────────────────────────────────────────────

    async def add_allergy(
        self, patient_id: uuid.UUID, data: AllergyCreate
    ) -> AllergyResponse:
        await self._load_patient(patient_id)
        allergy = Allergy(patient_id=patient_id, **data.model_dump())
        self.db.add(allergy)
        await self.db.commit()
        await self.db.refresh(allergy)
        return AllergyResponse.model_validate(allergy)

    # ── Chronic diseases ──────────────────────────────────────────────────────

    async def add_chronic_disease(
        self, patient_id: uuid.UUID, data: ChronicDiseaseCreate
    ) -> ChronicDiseaseResponse:
        await self._load_patient(patient_id)
        cd = ChronicDisease(patient_id=patient_id, **data.model_dump())
        self.db.add(cd)
        await self.db.flush()

        result = await self.db.execute(
            select(ChronicDisease)
            .where(ChronicDisease.id == cd.id)
            .options(selectinload(ChronicDisease.icd10))
        )
        cd = result.scalar_one()
        await self.db.commit()
        return ChronicDiseaseResponse.model_validate(cd)

    # ── Document upload ───────────────────────────────────────────────────────

    async def upload_document(
        self, patient_id: uuid.UUID, file: UploadFile, uploaded_by: User
    ) -> DocumentResponse:
        allowed_types = {"image/jpeg", "image/png", "application/pdf"}
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Allowed: {', '.join(allowed_types)}",
            )

        content = await file.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File size exceeds 10 MB limit")

        object_key = f"patients/{patient_id}/{uuid.uuid4()}_{file.filename}"
        bucket = settings.MINIO_BUCKET_DOCUMENTS
        minio = _get_minio()

        await _run_sync(
            minio.put_object,
            bucket,
            object_key,
            io.BytesIO(content),
            len(content),
            content_type=file.content_type,
        )

        protocol = "https" if settings.MINIO_USE_SSL else "http"
        file_url = f"{protocol}://{settings.MINIO_ENDPOINT}/{bucket}/{object_key}"

        doc = PatientDocument(
            patient_id=patient_id,
            file_name=file.filename,
            file_url=file_url,
            file_type=file.content_type,
            file_size=len(content),
            uploaded_by=uploaded_by.id,
        )
        self.db.add(doc)
        self.db.add(AuditLog(
            user_id=uploaded_by.id, action="UPLOAD_DOCUMENT",
            resource="patient_documents", resource_id=patient_id,
        ))
        await self.db.commit()
        await self.db.refresh(doc)
        return DocumentResponse.model_validate(doc)

    # ── Patient history ───────────────────────────────────────────────────────

    async def get_patient_history(
        self, patient_id: uuid.UUID
    ) -> list[EncounterSummary]:
        await self._load_patient(patient_id)
        result = await self.db.execute(
            select(Encounter)
            .where(Encounter.patient_id == patient_id)
            .options(selectinload(Encounter.diagnoses))
            .order_by(Encounter.started_at.desc())
        )
        encounters = result.scalars().all()
        return [EncounterSummary.model_validate(e) for e in encounters]

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _load_patient(self, patient_id: uuid.UUID) -> Patient:
        result = await self.db.execute(
            select(Patient).where(Patient.id == patient_id, Patient.is_active == True)
        )
        patient = result.scalar_one_or_none()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        return patient