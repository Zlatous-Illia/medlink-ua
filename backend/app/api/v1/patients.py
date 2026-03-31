from typing import Annotated, Optional
import uuid

from fastapi import APIRouter, Depends, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.core.database import get_db
from app.core.dependencies import get_redis, require_roles, get_current_user
from app.models.user import User, UserRole
from app.schemas.patients import (
    PatientCreate, PatientUpdate, PatientResponse,
    AllergyCreate, AllergyResponse,
    ChronicDiseaseCreate, ChronicDiseaseResponse,
    MedicalCardUpdate, MedicalCardResponse,
    DocumentResponse, EncounterSummary,
)
from app.services.patient_service import PatientService

router = APIRouter(prefix="/patients", tags=["Patients"])

# ─── Role dependencies ────────────────────────────────────────────────────────

_doctor_or_admin = require_roles(UserRole.DOCTOR, UserRole.ADMIN, UserRole.SUPER_ADMIN)
_doctor_admin_patient = require_roles(
    UserRole.DOCTOR, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.PATIENT
)
_doctor_only = require_roles(UserRole.DOCTOR, UserRole.SUPER_ADMIN)


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/", response_model=PatientResponse, status_code=201)
async def create_patient(
    data: PatientCreate,
    current_user: Annotated[User, Depends(_doctor_or_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    """Create a new patient record."""
    svc = PatientService(db, redis)
    return await svc.create_patient(data, created_by_user_id=current_user.id)


@router.get("/", response_model=list[PatientResponse])
async def list_patients(
    current_user: Annotated[User, Depends(_doctor_or_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    search: Optional[str] = Query(None, description="Search by name, tax_id, or phone"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """List patients with optional search."""
    svc = PatientService(db, redis)
    return await svc.get_patients(search=search, skip=skip, limit=limit)


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: uuid.UUID,
    current_user: Annotated[User, Depends(_doctor_admin_patient)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    """Get patient by ID. Patients can only access their own profile."""
    svc = PatientService(db, redis)
    return await svc.get_patient(patient_id, requesting_user=current_user)


@router.patch("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: uuid.UUID,
    data: PatientUpdate,
    current_user: Annotated[User, Depends(_doctor_or_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    """Partially update patient demographics."""
    svc = PatientService(db, redis)
    return await svc.update_patient(patient_id, data, updated_by=current_user)


@router.get("/{patient_id}/medical-card", response_model=MedicalCardResponse)
async def get_medical_card(
    patient_id: uuid.UUID,
    current_user: Annotated[User, Depends(_doctor_only)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    """Get patient's medical card including allergies and chronic diseases."""
    svc = PatientService(db, redis)
    return await svc.get_medical_card(patient_id, requesting_user=current_user)


@router.put("/{patient_id}/medical-card", response_model=MedicalCardResponse)
async def update_medical_card(
    patient_id: uuid.UUID,
    data: MedicalCardUpdate,
    current_user: Annotated[User, Depends(_doctor_only)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    """Update patient's medical card fields."""
    svc = PatientService(db, redis)
    return await svc.update_medical_card(patient_id, data, updated_by=current_user)


@router.post("/{patient_id}/allergies", response_model=AllergyResponse, status_code=201)
async def add_allergy(
    patient_id: uuid.UUID,
    data: AllergyCreate,
    current_user: Annotated[User, Depends(_doctor_or_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    """Add an allergy record to a patient."""
    svc = PatientService(db, redis)
    return await svc.add_allergy(patient_id, data)


@router.post("/{patient_id}/chronic-diseases", response_model=ChronicDiseaseResponse, status_code=201)
async def add_chronic_disease(
    patient_id: uuid.UUID,
    data: ChronicDiseaseCreate,
    current_user: Annotated[User, Depends(_doctor_only)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    """Add a chronic disease record to a patient."""
    svc = PatientService(db, redis)
    return await svc.add_chronic_disease(patient_id, data)


@router.post("/{patient_id}/documents", response_model=DocumentResponse, status_code=201)
async def upload_document(
    patient_id: uuid.UUID,
    current_user: Annotated[User, Depends(_doctor_or_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    file: UploadFile = File(...),
):
    """Upload a document (PDF/image) for a patient to MinIO storage."""
    svc = PatientService(db, redis)
    return await svc.upload_document(patient_id, file, uploaded_by=current_user)


@router.get("/{patient_id}/history", response_model=list[EncounterSummary])
async def get_history(
    patient_id: uuid.UUID,
    current_user: Annotated[User, Depends(_doctor_only)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    """Get patient's encounter history with diagnoses."""
    svc = PatientService(db, redis)
    return await svc.get_patient_history(patient_id)