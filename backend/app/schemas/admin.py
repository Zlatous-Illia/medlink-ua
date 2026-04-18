from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.user import UserRole


# ─── User management ──────────────────────────────────────────────────────────

class UserAdminResponse(BaseModel):
    id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    middle_name: Optional[str]
    phone: Optional[str]
    role: UserRole
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class UserAdminDetailResponse(UserAdminResponse):
    audit_events_count: int = 0


class UserAdminUpdate(BaseModel):
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


# ─── Audit log ────────────────────────────────────────────────────────────────

class AuditLogResponse(BaseModel):
    id: uuid.UUID
    user_id: Optional[uuid.UUID]
    action: str
    resource: Optional[str]
    resource_id: Optional[uuid.UUID]
    ip_address: Optional[str]
    details: Optional[dict]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ─── System stats ─────────────────────────────────────────────────────────────

class UsersStats(BaseModel):
    total: int
    by_role: dict[str, int]


class PatientsStats(BaseModel):
    total: int
    active: int


class EncountersStats(BaseModel):
    total: int
    last_30_days: int


class PrescriptionsStats(BaseModel):
    total: int
    active: int


class AppointmentsStats(BaseModel):
    total: int
    upcoming: int


class SystemStatsResponse(BaseModel):
    users: UsersStats
    patients: PatientsStats
    encounters: EncountersStats
    prescriptions: PrescriptionsStats
    appointments: AppointmentsStats
