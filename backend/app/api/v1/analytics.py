from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.core.database import get_db
from app.core.dependencies import get_redis, require_roles
from app.models.user import User, UserRole
from app.schemas.analytics import (
    GroupBy,
    AppointmentPeriodResponse,
    TopDiagnosisResponse,
    DoctorLoadResponse,
    PrescriptionPeriodResponse,
    CancellationRateResponse,
)
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])

_analytics_access = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DOCTOR)


# ─── 1. Appointments by period ────────────────────────────────────────────────

@router.get("/appointments", response_model=list[AppointmentPeriodResponse])
async def appointments_by_period(
    current_user: Annotated[User, Depends(_analytics_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    date_from: Optional[date] = Query(None, description="Початок діапазону (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="Кінець діапазону (YYYY-MM-DD)"),
    group_by: GroupBy = Query(GroupBy.day, description="Групування: day | week | month"),
):
    """Динаміка записів за обраний період із розбивкою на статуси."""
    return await AnalyticsService(db, redis).appointments_by_period(
        date_from, date_to, group_by, current_user
    )


# ─── 2. Top-10 ICD-10 diagnoses ──────────────────────────────────────────────

@router.get("/diagnoses/top10", response_model=list[TopDiagnosisResponse])
async def top_diagnoses(
    current_user: Annotated[User, Depends(_analytics_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    doctor_id: Optional[uuid.UUID] = Query(None, description="Фільтр по лікарю (ігнорується якщо роль DOCTOR)"),
):
    """Топ-10 діагнозів МКБ-10 за кількістю постановок."""
    return await AnalyticsService(db, redis).top_diagnoses(
        date_from, date_to, doctor_id, current_user
    )


# ─── 3. Doctor load ───────────────────────────────────────────────────────────

@router.get("/doctors/load", response_model=list[DoctorLoadResponse])
async def doctor_load(
    current_user: Annotated[User, Depends(_analytics_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
):
    """Навантаження лікарів: кількість прийомів та записів."""
    return await AnalyticsService(db, redis).doctor_load(date_from, date_to, current_user)


# ─── 4. Prescriptions by period ──────────────────────────────────────────────

@router.get("/prescriptions", response_model=list[PrescriptionPeriodResponse])
async def prescriptions_by_period(
    current_user: Annotated[User, Depends(_analytics_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    group_by: GroupBy = Query(GroupBy.day),
):
    """Кількість виписаних рецептів по часу."""
    return await AnalyticsService(db, redis).prescriptions_by_period(
        date_from, date_to, group_by, current_user
    )


# ─── 5. Cancellation rate ─────────────────────────────────────────────────────

@router.get("/appointments/cancellation-rate", response_model=CancellationRateResponse)
async def cancellation_rate(
    current_user: Annotated[User, Depends(_analytics_access)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    doctor_id: Optional[uuid.UUID] = Query(None),
):
    """Відсоток скасованих записів."""
    return await AnalyticsService(db, redis).cancellation_rate(
        date_from, date_to, doctor_id, current_user
    )
