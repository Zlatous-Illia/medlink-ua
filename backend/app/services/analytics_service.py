from __future__ import annotations

import uuid
from datetime import date, datetime, timezone, timedelta
from typing import Optional

import redis.asyncio as aioredis
from sqlalchemy import select, func, and_, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinical import (
    Encounter, Diagnosis, Prescription, PrescriptionStatus,
)
from app.models.doctor import Doctor
from app.models.reference import ICD10Code, Specialization
from app.models.scheduling import Appointment, AppointmentStatus
from app.models.user import User, UserRole
from app.schemas.analytics import (
    GroupBy,
    AppointmentPeriodResponse,
    TopDiagnosisResponse,
    DoctorLoadResponse,
    PrescriptionPeriodResponse,
    CancellationRateResponse,
)


def _default_date_range(
    date_from: Optional[date],
    date_to: Optional[date],
) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    dt_to = (
        datetime(date_to.year, date_to.month, date_to.day, 23, 59, 59, tzinfo=timezone.utc)
        if date_to else now
    )
    dt_from = (
        datetime(date_from.year, date_from.month, date_from.day, 0, 0, 0, tzinfo=timezone.utc)
        if date_from else now - timedelta(days=30)
    )
    return dt_from, dt_to


class AnalyticsService:

    def __init__(self, db: AsyncSession, redis: aioredis.Redis):
        self.db = db
        self.redis = redis

    # ── 1. Appointments by period ─────────────────────────────────────────────

    async def appointments_by_period(
        self,
        date_from: Optional[date],
        date_to: Optional[date],
        group_by: GroupBy,
        current_user: User,
    ) -> list[AppointmentPeriodResponse]:
        dt_from, dt_to = _default_date_range(date_from, date_to)

        period_expr = func.date_trunc(group_by.value, Appointment.slot_datetime)
        period_col = period_expr.label("period")

        query = (
            select(
                period_col,
                func.count(Appointment.id).label("total"),
                func.count(1).filter(
                    Appointment.status == AppointmentStatus.CANCELLED
                ).label("cancelled"),
                func.count(1).filter(
                    Appointment.status == AppointmentStatus.COMPLETED
                ).label("completed"),
            )
            .where(
                Appointment.slot_datetime >= dt_from,
                Appointment.slot_datetime <= dt_to,
            )
            .group_by(period_expr)
            .order_by(period_expr)
        )

        if current_user.role == UserRole.DOCTOR:
            doctor_id = await self._get_doctor_id(current_user)
            if doctor_id:
                query = query.where(Appointment.doctor_id == doctor_id)

        result = await self.db.execute(query)
        rows = result.fetchall()
        return [
            AppointmentPeriodResponse(
                period=row.period.isoformat() if row.period else "",
                total=row.total,
                cancelled=row.cancelled,
                completed=row.completed,
            )
            for row in rows
        ]

    # ── 2. Top-10 ICD-10 diagnoses ────────────────────────────────────────────

    async def top_diagnoses(
        self,
        date_from: Optional[date],
        date_to: Optional[date],
        doctor_id: Optional[uuid.UUID],
        current_user: User,
    ) -> list[TopDiagnosisResponse]:
        dt_from, dt_to = _default_date_range(date_from, date_to)

        count_col = func.count(Diagnosis.id).label("count")
        query = (
            select(
                ICD10Code.code.label("icd10_code"),
                ICD10Code.name_ua.label("name_ua"),
                count_col,
            )
            .join(Diagnosis, Diagnosis.icd10_id == ICD10Code.id)
            .join(Encounter, Encounter.id == Diagnosis.encounter_id)
            .where(
                Encounter.started_at >= dt_from,
                Encounter.started_at <= dt_to,
            )
            .group_by(ICD10Code.id, ICD10Code.code, ICD10Code.name_ua)
            .order_by(count_col.desc())
            .limit(10)
        )

        # Apply doctor filter
        effective_doctor_id = doctor_id
        if current_user.role == UserRole.DOCTOR:
            effective_doctor_id = await self._get_doctor_id(current_user)

        if effective_doctor_id:
            query = query.where(Encounter.doctor_id == effective_doctor_id)

        result = await self.db.execute(query)
        rows = result.fetchall()
        return [
            TopDiagnosisResponse(
                icd10_code=row.icd10_code,
                name_ua=row.name_ua,
                count=row.count,
            )
            for row in rows
        ]

    # ── 3. Doctor load ────────────────────────────────────────────────────────

    async def doctor_load(
        self,
        date_from: Optional[date],
        date_to: Optional[date],
        current_user: User,
    ) -> list[DoctorLoadResponse]:
        dt_from, dt_to = _default_date_range(date_from, date_to)

        enc_count = func.count(distinct(Encounter.id)).label("encounters_count")
        appt_count = func.count(distinct(Appointment.id)).label("appointments_count")

        query = (
            select(
                Doctor.id.label("doctor_id"),
                User.first_name,
                User.last_name,
                User.middle_name,
                Specialization.name_ua.label("specialization"),
                enc_count,
                appt_count,
            )
            .join(User, Doctor.user_id == User.id)
            .outerjoin(Specialization, Doctor.specialization_id == Specialization.id)
            .outerjoin(
                Encounter,
                and_(
                    Encounter.doctor_id == Doctor.id,
                    Encounter.started_at >= dt_from,
                    Encounter.started_at <= dt_to,
                ),
            )
            .outerjoin(
                Appointment,
                and_(
                    Appointment.doctor_id == Doctor.id,
                    Appointment.slot_datetime >= dt_from,
                    Appointment.slot_datetime <= dt_to,
                ),
            )
            .where(Doctor.is_active == True)
            .group_by(
                Doctor.id,
                User.first_name,
                User.last_name,
                User.middle_name,
                Specialization.name_ua,
            )
            .order_by(enc_count.desc())
        )

        if current_user.role == UserRole.DOCTOR:
            doctor_id = await self._get_doctor_id(current_user)
            if doctor_id:
                query = query.where(Doctor.id == doctor_id)

        result = await self.db.execute(query)
        rows = result.fetchall()

        return [
            DoctorLoadResponse(
                doctor_id=row.doctor_id,
                full_name=_build_full_name(row.last_name, row.first_name, row.middle_name),
                specialization=row.specialization,
                encounters_count=row.encounters_count,
                appointments_count=row.appointments_count,
            )
            for row in rows
        ]

    # ── 4. Prescriptions by period ────────────────────────────────────────────

    async def prescriptions_by_period(
        self,
        date_from: Optional[date],
        date_to: Optional[date],
        group_by: GroupBy,
        current_user: User,
    ) -> list[PrescriptionPeriodResponse]:
        dt_from, dt_to = _default_date_range(date_from, date_to)

        period_expr = func.date_trunc(group_by.value, Prescription.created_at)
        period_col = period_expr.label("period")

        query = (
            select(
                period_col,
                func.count(Prescription.id).label("total"),
                func.count(1).filter(
                    Prescription.status == PrescriptionStatus.ACTIVE
                ).label("active"),
                func.count(1).filter(
                    Prescription.status == PrescriptionStatus.CANCELLED
                ).label("cancelled"),
            )
            .where(
                Prescription.created_at >= dt_from,
                Prescription.created_at <= dt_to,
            )
            .group_by(period_expr)
            .order_by(period_expr)
        )

        if current_user.role == UserRole.DOCTOR:
            doctor_id = await self._get_doctor_id(current_user)
            if doctor_id:
                query = query.where(Prescription.doctor_id == doctor_id)

        result = await self.db.execute(query)
        rows = result.fetchall()
        return [
            PrescriptionPeriodResponse(
                period=row.period.isoformat() if row.period else "",
                total=row.total,
                active=row.active,
                cancelled=row.cancelled,
            )
            for row in rows
        ]

    # ── 5. Cancellation rate ──────────────────────────────────────────────────

    async def cancellation_rate(
        self,
        date_from: Optional[date],
        date_to: Optional[date],
        doctor_id: Optional[uuid.UUID],
        current_user: User,
    ) -> CancellationRateResponse:
        dt_from, dt_to = _default_date_range(date_from, date_to)

        query = (
            select(
                func.count(Appointment.id).label("total"),
                func.count(1).filter(
                    Appointment.status == AppointmentStatus.CANCELLED
                ).label("cancelled"),
            )
            .where(
                Appointment.slot_datetime >= dt_from,
                Appointment.slot_datetime <= dt_to,
            )
        )

        # Apply doctor filter
        effective_doctor_id = doctor_id
        if current_user.role == UserRole.DOCTOR:
            effective_doctor_id = await self._get_doctor_id(current_user)

        if effective_doctor_id:
            query = query.where(Appointment.doctor_id == effective_doctor_id)

        result = await self.db.execute(query)
        row = result.one()

        total = row.total or 0
        cancelled = row.cancelled or 0
        rate = round(cancelled / total * 100, 2) if total > 0 else 0.0

        return CancellationRateResponse(
            total_appointments=total,
            cancelled=cancelled,
            cancellation_rate=rate,
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _get_doctor_id(self, user: User) -> Optional[uuid.UUID]:
        result = await self.db.execute(
            select(Doctor.id).where(Doctor.user_id == user.id)
        )
        return result.scalar_one_or_none()


def _build_full_name(
    last_name: str, first_name: str, middle_name: Optional[str]
) -> str:
    parts = [last_name, first_name]
    if middle_name:
        parts.append(middle_name)
    return " ".join(parts)
