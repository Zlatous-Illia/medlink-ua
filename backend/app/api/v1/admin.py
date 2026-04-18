from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.core.database import get_db
from app.core.dependencies import get_redis, require_roles
from app.models.user import User, UserRole
from app.schemas.admin import (
    UserAdminResponse,
    UserAdminDetailResponse,
    UserAdminUpdate,
    AuditLogResponse,
    SystemStatsResponse,
)
from app.schemas.auth import UserRegisterRequest
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["Admin"])

_admin_only = require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)


# ─── Users ────────────────────────────────────────────────────────────────────

@router.post("/users", response_model=UserAdminDetailResponse, status_code=201)
async def create_user(
    data: UserRegisterRequest,
    current_user: Annotated[User, Depends(_admin_only)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    """Створити нового користувача будь-якої ролі (тільки ADMIN/SUPER_ADMIN)."""
    return await AdminService(db, redis).create_user(data, current_user)


@router.get("/users", response_model=list[UserAdminResponse])
async def list_users(
    current_user: Annotated[User, Depends(_admin_only)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    role: Optional[UserRole] = Query(None, description="Фільтр за роллю"),
    is_active: Optional[bool] = Query(None, description="Фільтр за активністю"),
    search: Optional[str] = Query(None, description="Пошук по email / ПІБ"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """Список усіх користувачів із фільтрами."""
    return await AdminService(db, redis).list_users(role, is_active, search, skip, limit)


@router.get("/users/{user_id}", response_model=UserAdminDetailResponse)
async def get_user(
    user_id: uuid.UUID,
    current_user: Annotated[User, Depends(_admin_only)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    """Деталі користувача + кількість audit-подій."""
    return await AdminService(db, redis).get_user(user_id)


@router.patch("/users/{user_id}", response_model=UserAdminDetailResponse)
async def update_user(
    user_id: uuid.UUID,
    data: UserAdminUpdate,
    current_user: Annotated[User, Depends(_admin_only)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    """Змінити is_active або role. SUPER_ADMIN захищений від зниження."""
    return await AdminService(db, redis).update_user(user_id, data, current_user)


@router.post("/users/{user_id}/deactivate", response_model=UserAdminDetailResponse)
async def deactivate_user(
    user_id: uuid.UUID,
    current_user: Annotated[User, Depends(_admin_only)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    """Деактивувати користувача + відкликати всі refresh-токени."""
    return await AdminService(db, redis).deactivate_user(user_id, current_user)


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: uuid.UUID,
    current_user: Annotated[User, Depends(_admin_only)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    """Повністю видалити користувача (тільки SUPER_ADMIN захищений)."""
    await AdminService(db, redis).delete_user(user_id, current_user)


# ─── Audit log ────────────────────────────────────────────────────────────────

@router.get("/audit-logs", response_model=list[AuditLogResponse])
async def list_audit_logs(
    current_user: Annotated[User, Depends(_admin_only)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    user_id: Optional[uuid.UUID] = Query(None),
    action: Optional[str] = Query(None, description="ILIKE пошук по назві дії"),
    resource: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """Журнал дій з фільтрами."""
    return await AdminService(db, redis).list_audit_logs(
        user_id, action, resource, date_from, date_to, skip, limit
    )


# ─── Stats ────────────────────────────────────────────────────────────────────

@router.get("/stats", response_model=SystemStatsResponse)
async def get_stats(
    current_user: Annotated[User, Depends(_admin_only)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    """Агрегована системна статистика."""
    return await AdminService(db, redis).get_stats()
