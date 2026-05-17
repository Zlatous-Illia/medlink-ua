from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.core.database import get_db
from app.core.dependencies import get_redis, require_doctor, require_admin, get_current_user, require_roles
from app.models.user import User, UserRole
from app.schemas.appointments import (
    AppointmentCreate, AppointmentResponse, AppointmentCancelRequest,
    DoctorListResponse, SlotResponse, ScheduleCreate, ScheduleResponse,
)
from app.services.appointment_service import AppointmentService
from app.services.encounter_service import EncounterService
from app.schemas.encounters import AppointmentTodayResponse

router = APIRouter(prefix="/appointments", tags=["Appointments"])
doctors_router = APIRouter(prefix="/doctors", tags=["Doctors"])

_doctor_or_patient = require_roles(
    UserRole.DOCTOR, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.PATIENT
)
_patient_only = require_roles(UserRole.PATIENT)


@router.get("/today", response_model=list[AppointmentTodayResponse])
async def get_today_appointments(
    current_user: Annotated[User, Depends(require_doctor)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    return await EncounterService(db, redis).get_today_appointments(current_user)


@router.get("", response_model=list[AppointmentResponse])
async def list_appointments(
    current_user: Annotated[User, Depends(_doctor_or_patient)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    return await AppointmentService(db, redis).list_appointments(current_user, skip, limit)


@router.post("", response_model=AppointmentResponse, status_code=201)
async def create_appointment(
    data: AppointmentCreate,
    current_user: Annotated[User, Depends(_patient_only)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    return await AppointmentService(db, redis).create_appointment(data, current_user)


@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(
    appointment_id: uuid.UUID,
    current_user: Annotated[User, Depends(_doctor_or_patient)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    return await AppointmentService(db, redis).get_appointment(appointment_id, current_user)


@router.patch("/{appointment_id}/cancel", response_model=AppointmentResponse)
async def cancel_appointment(
    appointment_id: uuid.UUID,
    data: AppointmentCancelRequest,
    current_user: Annotated[User, Depends(_doctor_or_patient)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    return await AppointmentService(db, redis).cancel_appointment(appointment_id, data, current_user)


@doctors_router.get("", response_model=list[DoctorListResponse])
async def list_doctors(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    specialization_id: Optional[uuid.UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    return await AppointmentService(db, redis).list_doctors(specialization_id, skip, limit)


@doctors_router.get("/{doctor_id}/slots", response_model=list[SlotResponse])
async def get_doctor_slots(
    doctor_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    date: date = Query(...),
):
    return await AppointmentService(db, redis).get_doctor_slots(doctor_id, date)


@doctors_router.post("/{doctor_id}/schedule", response_model=ScheduleResponse, status_code=201)
async def create_schedule(
    doctor_id: uuid.UUID,
    data: ScheduleCreate,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    return await AppointmentService(db, redis).create_schedule(doctor_id, data, current_user)


@doctors_router.get("/{doctor_id}/schedule", response_model=list[ScheduleResponse])
async def get_schedule(
    doctor_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    return await AppointmentService(db, redis).get_schedule(doctor_id)
