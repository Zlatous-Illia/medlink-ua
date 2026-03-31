from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.core.database import get_db
from app.core.dependencies import get_redis, require_roles, get_current_user
from app.models.user import User, UserRole
from app.models.clinical import PrescriptionStatus
from app.schemas.patient_cabinet import (
    UserProfileResponse, ProfileUpdate,
    MedicalCardReadResponse,
    MyEncounterResponse,
    MyPrescriptionResponse,
    MyDocumentResponse,
    ChangePasswordRequest,
)
from app.services.patient_cabinet_service import PatientCabinetService

router = APIRouter(prefix="/me", tags=["Patient Cabinet"])

_patient_only = require_roles(UserRole.PATIENT)


@router.get("", response_model=UserProfileResponse)
async def get_profile(
    current_user: Annotated[User, Depends(_patient_only)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    """Власний профіль пацієнта."""
    return await PatientCabinetService(db, redis).get_profile(current_user)


@router.patch("", response_model=UserProfileResponse)
async def update_profile(
    data: ProfileUpdate,
    current_user: Annotated[User, Depends(_patient_only)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    """Оновити контактні дані (ПІБ, телефон). Email не змінюється."""
    return await PatientCabinetService(db, redis).update_profile(current_user, data)


@router.post("/avatar", response_model=UserProfileResponse)
async def upload_avatar(
    current_user: Annotated[User, Depends(_patient_only)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    file: UploadFile = File(...),
):
    """Завантажити аватар (JPEG/PNG, макс. 5 МБ) → MinIO medlink-avatars."""
    return await PatientCabinetService(db, redis).upload_avatar(current_user, file)


@router.get("/medical-card", response_model=MedicalCardReadResponse)
async def get_medical_card(
    current_user: Annotated[User, Depends(_patient_only)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    """Власна медична картка (тільки читання)."""
    return await PatientCabinetService(db, redis).get_medical_card(current_user)


@router.get("/encounters", response_model=list[MyEncounterResponse])
async def get_encounters(
    current_user: Annotated[User, Depends(_patient_only)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    """Власна історія прийомів із діагнозами."""
    return await PatientCabinetService(db, redis).get_encounters(current_user)


@router.get("/prescriptions", response_model=list[MyPrescriptionResponse])
async def get_prescriptions(
    current_user: Annotated[User, Depends(_patient_only)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    status: Optional[PrescriptionStatus] = Query(None, description="Фільтр за статусом рецепту"),
):
    """Власні рецепти (активні та скасовані)."""
    return await PatientCabinetService(db, redis).get_prescriptions(current_user, status)


@router.get("/documents", response_model=list[MyDocumentResponse])
async def get_documents(
    current_user: Annotated[User, Depends(_patient_only)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    """Список завантажених документів пацієнта."""
    return await PatientCabinetService(db, redis).get_documents(current_user)


@router.patch("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    current_user: Annotated[User, Depends(_patient_only)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    """Змінити пароль. Відкликає всі активні refresh-токени."""
    return await PatientCabinetService(db, redis).change_password(
        current_user, data.current_password, data.new_password
    )
