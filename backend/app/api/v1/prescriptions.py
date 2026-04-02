from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.core.database import get_db
from app.core.dependencies import get_redis, require_doctor, require_roles
from app.models.user import User, UserRole
from app.schemas.prescriptions import (
    PrescriptionCreate, PrescriptionResponse,
    PrescriptionCancelRequest, DrugResponse,
)
from app.services.prescription_service import PrescriptionService

router = APIRouter(prefix="/prescriptions", tags=["Prescriptions"])

_doctor_or_patient = require_roles(
    UserRole.DOCTOR, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.PATIENT
)


@router.post("", response_model=PrescriptionResponse, status_code=201)
async def create_prescription(
    data: PrescriptionCreate,
    current_user: Annotated[User, Depends(require_doctor)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    return await PrescriptionService(db, redis).create_prescription(data, current_user)


@router.get("/drugs/search", response_model=list[DrugResponse])
async def search_drugs(
    current_user: Annotated[User, Depends(require_doctor)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=50),
):
    return await PrescriptionService(db, redis).search_drugs(q, limit)


@router.get("/patients/{patient_id}/prescriptions", response_model=list[PrescriptionResponse])
async def get_patient_prescriptions(
    patient_id: uuid.UUID,
    current_user: Annotated[User, Depends(_doctor_or_patient)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    return await PrescriptionService(db, redis).get_patient_prescriptions(patient_id, current_user)


@router.get("/{prescription_id}", response_model=PrescriptionResponse)
async def get_prescription(
    prescription_id: uuid.UUID,
    current_user: Annotated[User, Depends(_doctor_or_patient)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    return await PrescriptionService(db, redis).get_prescription(prescription_id, current_user)


@router.patch("/{prescription_id}/cancel", response_model=PrescriptionResponse)
async def cancel_prescription(
    prescription_id: uuid.UUID,
    data: PrescriptionCancelRequest,
    current_user: Annotated[User, Depends(require_doctor)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    return await PrescriptionService(db, redis).cancel_prescription(prescription_id, data, current_user)
