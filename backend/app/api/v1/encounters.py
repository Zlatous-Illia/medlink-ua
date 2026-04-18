from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.core.database import get_db
from app.core.dependencies import get_redis, require_doctor, get_current_user, require_roles
from app.models.user import User, UserRole
from app.schemas.encounters import (
    EncounterCreate, EncounterUpdate, EncounterResponse,
    DiagnosisCreate, DiagnosisResponse,
    AppointmentTodayResponse, ICD10SearchResponse,
    ReferralCreate, ReferralResponse, ReferralUpdate,
)
from app.services.encounter_service import EncounterService

router = APIRouter(prefix="/encounters", tags=["Encounters"])
icd10_router = APIRouter(prefix="/icd10", tags=["ICD-10"])


_doctor_or_patient = require_roles(
    UserRole.DOCTOR, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.PATIENT
)


@router.post("", response_model=EncounterResponse, status_code=201)
async def create_encounter(
    data: EncounterCreate,
    current_user: Annotated[User, Depends(require_doctor)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    return await EncounterService(db, redis).create_encounter(data, current_user)


@router.get("/{encounter_id}", response_model=EncounterResponse)
async def get_encounter(
    encounter_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_doctor)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    return await EncounterService(db, redis).get_encounter(encounter_id, current_user)


@router.patch("/{encounter_id}", response_model=EncounterResponse)
async def update_encounter(
    encounter_id: uuid.UUID,
    data: EncounterUpdate,
    current_user: Annotated[User, Depends(require_doctor)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    return await EncounterService(db, redis).update_encounter(encounter_id, data, current_user)


@router.post("/{encounter_id}/cancel", response_model=EncounterResponse)
async def cancel_encounter(
    encounter_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_doctor)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    return await EncounterService(db, redis).cancel_encounter(encounter_id, current_user)


@router.delete("/{encounter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_encounter(
    encounter_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_doctor)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    await EncounterService(db, redis).delete_encounter(encounter_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{encounter_id}/complete", response_model=EncounterResponse)
async def complete_encounter(
    encounter_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_doctor)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    return await EncounterService(db, redis).complete_encounter(encounter_id, current_user)


@router.get("/{encounter_id}/pdf")
async def get_encounter_pdf(
    encounter_id: uuid.UUID,
    current_user: Annotated[User, Depends(_doctor_or_patient)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    pdf_bytes = await EncounterService(db, redis).get_encounter_pdf(encounter_id, current_user)
    return Response(content=pdf_bytes, media_type="application/pdf")


@router.post("/{encounter_id}/diagnoses", response_model=DiagnosisResponse, status_code=201)
async def add_diagnosis(
    encounter_id: uuid.UUID,
    data: DiagnosisCreate,
    current_user: Annotated[User, Depends(require_doctor)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    return await EncounterService(db, redis).add_diagnosis(encounter_id, data, current_user)


@router.get("/patients/{patient_id}/encounters", response_model=list[EncounterResponse])
async def get_patient_encounters(
    patient_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_doctor)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    return await EncounterService(db, redis).get_patient_encounters(patient_id)


@router.post("/{encounter_id}/referrals", response_model=ReferralResponse, status_code=201)
async def create_referral(
    encounter_id: uuid.UUID,
    data: ReferralCreate,
    current_user: Annotated[User, Depends(require_doctor)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    data.encounter_id = encounter_id
    return await EncounterService(db, redis).create_referral(data, current_user)


@router.get("/referrals/{referral_id}", response_model=ReferralResponse)
async def get_referral(
    referral_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_doctor)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    return await EncounterService(db, redis).get_referral(referral_id, current_user)


@router.patch("/referrals/{referral_id}", response_model=ReferralResponse)
async def update_referral(
    referral_id: uuid.UUID,
    data: ReferralUpdate,
    current_user: Annotated[User, Depends(require_doctor)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    return await EncounterService(db, redis).update_referral(referral_id, data, current_user)


@router.post("/referrals/{referral_id}/cancel", response_model=ReferralResponse)
async def cancel_referral(
    referral_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_doctor)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    return await EncounterService(db, redis).cancel_referral(referral_id, current_user)


@router.delete("/referrals/{referral_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_referral(
    referral_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_doctor)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    await EncounterService(db, redis).delete_referral(referral_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/patients/{patient_id}/referrals", response_model=list[ReferralResponse])
async def get_patient_referrals(
    patient_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_doctor)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    return await EncounterService(db, redis).get_patient_referrals(patient_id)


@icd10_router.get("/search", response_model=list[ICD10SearchResponse])
async def search_icd10(
    current_user: Annotated[User, Depends(require_doctor)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=50),
):
    return await EncounterService(db, redis).search_icd10(q, limit)
