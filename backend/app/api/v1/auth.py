from typing import Annotated
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.core.database import get_db
from app.core.dependencies import get_redis, get_current_user
from app.models.user import User
from app.schemas.auth import (
    UserRegisterRequest, UserLoginRequest, OTPVerifyRequest,
    RefreshTokenRequest, TokenResponse, LoginStep1Response,
    UserResponse, ForgotPasswordRequest, ResetPasswordRequest,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    data: UserRegisterRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    """Register a new user."""
    svc = AuthService(db, redis)
    return await svc.register(data, ip=_ip(request))


@router.post("/login", response_model=LoginStep1Response)
async def login(
    data: UserLoginRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    """Step 1: verify password, send OTP to email."""
    svc = AuthService(db, redis)
    return await svc.login_step1(data, ip=_ip(request))


@router.post("/login/2fa", response_model=TokenResponse)
async def verify_otp(
    data: OTPVerifyRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    """Step 2: verify OTP code, issue JWT tokens."""
    svc = AuthService(db, redis)
    return await svc.login_step2(
        data, ip=_ip(request),
        user_agent=request.headers.get("user-agent", ""),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    data: RefreshTokenRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    """Refresh access token using refresh token."""
    svc = AuthService(db, redis)
    return await svc.refresh_tokens(data.refresh_token, ip=_ip(request))


@router.post("/logout")
async def logout(
    data: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
):
    """Revoke refresh token."""
    svc = AuthService(db, redis)
    return await svc.logout(data.refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: Annotated[User, Depends(get_current_user)]):
    """Get current user profile."""
    return current_user
