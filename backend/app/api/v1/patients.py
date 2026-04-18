from typing import Annotated, Optional
import uuid

from fastapi import APIRouter, Depends, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.core.database import get_db
from app.core.dependencies import get_redis, require_roles, get_current_user, require_doctor, require_admin
from app.models.user import User, UserRole
from app.schemas.patients import (
    PatientCreate, PatientUpdate, PatientResponse,
    AllergyCreate, AllergyUpdate, AllergyResponse,
    ChronicDiseaseCreate, ChronicDiseaseUpdate, ChronicDiseaseResponse,
    MedicalCardUpdate, MedicalCardResponse,
    DocumentResponse, EncounterSummary,
    AllergenResponse,
)
from app.services.patient_service import PatientService

router = APIRouter(prefix="/patients", tags=["Patients"])

# ─── Role dependencies ────────────────────────────────────────────────────────

_doctor_admin_patient = require_roles(
    UserRole.DOCTOR, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.PATIENT
)
_admin_only = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)


# ─── Patients ─────────────────────────────────────────────────────────────────

@router.post("", response_model=PatientResponse, status_code=201)
async def create_patient(
    data: PatientCreate,
    current_user: Annotated[User, Depends(require_doctor)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    return await PatientService(db, redis).create_patient(data, created_by_user_id=current_user.id)


@router.get("", response_model=list[PatientResponse])
async def list_patients(
    current_user: Annotated[User, Depends(require_doctor)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    search: Optional[str] = Query(None, description="Search by name, tax_id, or phone"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    return await PatientService(db, redis).get_patients(search=search, skip=skip, limit=limit)


@router.delete("/{patient_id}", status_code=204)
async def deactivate_patient(
    patient_id: uuid.UUID,
    current_user: Annotated[User, Depends(_admin_only)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    """Деактивувати пацієнта без облікового запису (soft delete). Тільки ADMIN."""
    await PatientService(db, redis).deactivate_patient(patient_id, current_user)


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: uuid.UUID,
    current_user: Annotated[User, Depends(_doctor_admin_patient)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    return await PatientService(db, redis).get_patient(patient_id, requesting_user=current_user)


@router.patch("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: uuid.UUID,
    data: PatientUpdate,
    current_user: Annotated[User, Depends(require_doctor)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    return await PatientService(db, redis).update_patient(patient_id, data, updated_by=current_user)


# ─── Medical card ─────────────────────────────────────────────────────────────

@router.get("/{patient_id}/medical-card", response_model=MedicalCardResponse)
async def get_medical_card(
    patient_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_doctor)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    return await PatientService(db, redis).get_medical_card(patient_id, requesting_user=current_user)


@router.put("/{patient_id}/medical-card", response_model=MedicalCardResponse)
async def update_medical_card(
    patient_id: uuid.UUID,
    data: MedicalCardUpdate,
    current_user: Annotated[User, Depends(require_doctor)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    return await PatientService(db, redis).update_medical_card(patient_id, data, updated_by=current_user)


# ─── Allergies ────────────────────────────────────────────────────────────────

@router.post("/{patient_id}/allergies", response_model=AllergyResponse, status_code=201)
async def add_allergy(
    patient_id: uuid.UUID,
    data: AllergyCreate,
    current_user: Annotated[User, Depends(require_doctor)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    return await PatientService(db, redis).add_allergy(patient_id, data)


@router.patch("/{patient_id}/allergies/{allergy_id}", response_model=AllergyResponse)
async def update_allergy(
    patient_id: uuid.UUID,
    allergy_id: uuid.UUID,
    data: AllergyUpdate,
    current_user: Annotated[User, Depends(require_doctor)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    return await PatientService(db, redis).update_allergy(patient_id, allergy_id, data)


@router.delete("/{patient_id}/allergies/{allergy_id}", status_code=204)
async def delete_allergy(
    patient_id: uuid.UUID,
    allergy_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_doctor)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    await PatientService(db, redis).delete_allergy(patient_id, allergy_id)


# ─── Chronic diseases ─────────────────────────────────────────────────────────

@router.post("/{patient_id}/chronic-diseases", response_model=ChronicDiseaseResponse, status_code=201)
async def add_chronic_disease(
    patient_id: uuid.UUID,
    data: ChronicDiseaseCreate,
    current_user: Annotated[User, Depends(require_doctor)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    return await PatientService(db, redis).add_chronic_disease(patient_id, data)


@router.patch("/{patient_id}/chronic-diseases/{disease_id}", response_model=ChronicDiseaseResponse)
async def update_chronic_disease(
    patient_id: uuid.UUID,
    disease_id: uuid.UUID,
    data: ChronicDiseaseUpdate,
    current_user: Annotated[User, Depends(require_doctor)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    return await PatientService(db, redis).update_chronic_disease(patient_id, disease_id, data)


@router.delete("/{patient_id}/chronic-diseases/{disease_id}", status_code=204)
async def delete_chronic_disease(
    patient_id: uuid.UUID,
    disease_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_doctor)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    await PatientService(db, redis).delete_chronic_disease(patient_id, disease_id)


# ─── Documents ────────────────────────────────────────────────────────────────

@router.post("/{patient_id}/documents", response_model=DocumentResponse, status_code=201)
async def upload_document(
    patient_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_doctor)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    file: UploadFile = File(...),
):
    return await PatientService(db, redis).upload_document(patient_id, file, uploaded_by=current_user)


@router.get("/{patient_id}/documents", response_model=list[DocumentResponse])
async def get_documents(
    patient_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_doctor)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    return await PatientService(db, redis).get_documents(patient_id)


@router.delete("/{patient_id}/documents/{document_id}", status_code=204)
async def delete_document(
    patient_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_doctor)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    await PatientService(db, redis).delete_document(patient_id, document_id, deleted_by=current_user)


# ─── History ──────────────────────────────────────────────────────────────────

@router.get("/{patient_id}/history", response_model=list[EncounterSummary])
async def get_history(
    patient_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_doctor)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    return await PatientService(db, redis).get_patient_history(patient_id)


# ─── Allergens ────────────────────────────────────────────────────────────────

@router.get("/allergens/search", response_model=list[AllergenResponse])
async def search_allergens(
    current_user: Annotated[User, Depends(require_doctor)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=50),
):
    return await PatientService(db, redis).search_allergens(q, limit)
