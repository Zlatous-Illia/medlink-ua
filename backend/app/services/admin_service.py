from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

import redis.asyncio as aioredis
from fastapi import HTTPException
from sqlalchemy import select, update, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinical import Encounter, Prescription, PrescriptionStatus
from app.models.patient import Patient
from app.models.scheduling import Appointment, AppointmentStatus
from app.models.user import User, UserRole, RefreshToken, AuditLog
from app.schemas.admin import (
    UserAdminResponse,
    UserAdminDetailResponse,
    UserAdminUpdate,
    AuditLogResponse,
    SystemStatsResponse,
    UsersStats,
    PatientsStats,
    EncountersStats,
    PrescriptionsStats,
    AppointmentsStats,
)


class AdminService:

    def __init__(self, db: AsyncSession, redis: aioredis.Redis):
        self.db = db
        self.redis = redis

    # ── List users ────────────────────────────────────────────────────────────

    async def list_users(
        self,
        role: Optional[UserRole],
        is_active: Optional[bool],
        search: Optional[str],
        skip: int,
        limit: int,
    ) -> list[UserAdminResponse]:
        query = select(User)

        if role is not None:
            query = query.where(User.role == role)
        if is_active is not None:
            query = query.where(User.is_active == is_active)
        if search:
            pattern = f"%{search}%"
            query = query.where(
                User.email.ilike(pattern)
                | User.first_name.ilike(pattern)
                | User.last_name.ilike(pattern)
            )

        query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        users = result.scalars().all()
        return [UserAdminResponse.model_validate(u) for u in users]

    # ── Get user detail ───────────────────────────────────────────────────────

    async def get_user(self, user_id: uuid.UUID) -> UserAdminDetailResponse:
        user = await self.db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        count_result = await self.db.execute(
            select(func.count(AuditLog.id)).where(AuditLog.user_id == user_id)
        )
        audit_count = count_result.scalar_one()

        resp = UserAdminDetailResponse.model_validate(user)
        resp.audit_events_count = audit_count
        return resp

    # ── Update user ───────────────────────────────────────────────────────────

    async def update_user(
        self,
        user_id: uuid.UUID,
        data: UserAdminUpdate,
        current_user: User,
    ) -> UserAdminDetailResponse:
        user = await self.db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Guard: only SUPER_ADMIN can change role of SUPER_ADMIN
        if data.role is not None:
            if user.role == UserRole.SUPER_ADMIN and current_user.role != UserRole.SUPER_ADMIN:
                raise HTTPException(
                    status_code=403,
                    detail="Тільки SUPER_ADMIN може змінювати роль іншого SUPER_ADMIN",
                )

        changes: dict = {}
        if data.is_active is not None:
            changes["is_active"] = data.is_active
            user.is_active = data.is_active

            # Revoke all refresh tokens on deactivation
            if not data.is_active:
                await self.db.execute(
                    update(RefreshToken)
                    .where(RefreshToken.user_id == user_id)
                    .values(is_revoked=True)
                )

        if data.role is not None:
            changes["role"] = data.role.value
            user.role = data.role

        if changes:
            self.db.add(AuditLog(
                user_id=current_user.id,
                action="ADMIN_UPDATE_USER",
                resource="users",
                resource_id=user_id,
                details=changes,
            ))
            await self.db.commit()
            await self.db.refresh(user)

        return await self.get_user(user_id)

    # ── Deactivate user ───────────────────────────────────────────────────────

    async def deactivate_user(
        self, user_id: uuid.UUID, current_user: User
    ) -> UserAdminDetailResponse:
        return await self.update_user(
            user_id,
            UserAdminUpdate(is_active=False),
            current_user,
        )

    # ── Audit logs ────────────────────────────────────────────────────────────

    async def list_audit_logs(
        self,
        user_id: Optional[uuid.UUID],
        action: Optional[str],
        resource: Optional[str],
        date_from: Optional[datetime],
        date_to: Optional[datetime],
        skip: int,
        limit: int,
    ) -> list[AuditLogResponse]:
        query = select(AuditLog)

        if user_id is not None:
            query = query.where(AuditLog.user_id == user_id)
        if action:
            query = query.where(AuditLog.action.ilike(f"%{action}%"))
        if resource:
            query = query.where(AuditLog.resource == resource)
        if date_from:
            query = query.where(AuditLog.created_at >= date_from)
        if date_to:
            query = query.where(AuditLog.created_at <= date_to)

        query = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        logs = result.scalars().all()
        return [AuditLogResponse.model_validate(log) for log in logs]

    # ── System stats ──────────────────────────────────────────────────────────

    async def get_stats(self) -> SystemStatsResponse:
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)

        # Users: total + by role
        role_result = await self.db.execute(
            select(User.role, func.count(User.id)).group_by(User.role)
        )
        by_role: dict[str, int] = {}
        total_users = 0
        for row in role_result:
            by_role[row[0].value] = row[1]
            total_users += row[1]
        # Ensure all roles present
        for r in UserRole:
            by_role.setdefault(r.value, 0)

        # Patients: total + active
        patients_result = await self.db.execute(
            select(
                func.count(Patient.id).label("total"),
                func.count(1).filter(Patient.is_active == True).label("active"),
            )
        )
        p_row = patients_result.one()

        # Encounters: total + last 30 days
        encounters_result = await self.db.execute(
            select(
                func.count(Encounter.id).label("total"),
                func.count(1).filter(Encounter.started_at >= thirty_days_ago).label("recent"),
            )
        )
        e_row = encounters_result.one()

        # Prescriptions: total + active
        prescriptions_result = await self.db.execute(
            select(
                func.count(Prescription.id).label("total"),
                func.count(1).filter(Prescription.status == PrescriptionStatus.ACTIVE).label("active"),
            )
        )
        rx_row = prescriptions_result.one()

        # Appointments: total + upcoming (slot_datetime > now)
        appointments_result = await self.db.execute(
            select(
                func.count(Appointment.id).label("total"),
                func.count(1).filter(Appointment.slot_datetime > now).label("upcoming"),
            )
        )
        a_row = appointments_result.one()

        return SystemStatsResponse(
            users=UsersStats(total=total_users, by_role=by_role),
            patients=PatientsStats(total=p_row.total, active=p_row.active),
            encounters=EncountersStats(total=e_row.total, last_30_days=e_row.recent),
            prescriptions=PrescriptionsStats(total=rx_row.total, active=rx_row.active),
            appointments=AppointmentsStats(total=a_row.total, upcoming=a_row.upcoming),
        )
