import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import redis.asyncio as aioredis
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    hash_password, verify_password, create_access_token,
    create_refresh_token, decode_token, generate_otp,
    otp_redis_key, failed_attempts_key, lockout_redis_key,
)
from app.models.user import User, UserRole, RefreshToken, AuditLog
from app.schemas.auth import (
    UserRegisterRequest, UserLoginRequest, OTPVerifyRequest,
    TokenResponse, LoginStep1Response, UserResponse,
)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class AuthService:

    def __init__(self, db: AsyncSession, redis: aioredis.Redis):
        self.db = db
        self.redis = redis

    # ─── Register ────────────────────────────────────────────────────────────

    async def register(self, data: UserRegisterRequest, ip: str = None) -> UserResponse:
        # Check duplicate email
        existing = await self.db.execute(select(User).where(User.email == data.email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already registered")

        user = User(
            email=data.email,
            password_hash=hash_password(data.password),
            role=data.role,
            first_name=data.first_name,
            last_name=data.last_name,
            middle_name=data.middle_name,
            phone=data.phone,
        )
        self.db.add(user)
        await self.db.flush()  # get user.id

        # Audit
        self.db.add(AuditLog(
            user_id=user.id, action="REGISTER",
            resource="users", resource_id=user.id, ip_address=ip
        ))
        await self.db.commit()
        await self.db.refresh(user)
        return UserResponse.model_validate(user)

    # ─── Login Step 1: password check ────────────────────────────────────────

    async def login_step1(self, data: UserLoginRequest, ip: str = None) -> LoginStep1Response:
        user = await self._get_user_by_email(data.email)

        # Check lockout
        locked = await self.redis.get(lockout_redis_key(str(user.id)))
        if locked:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Account temporarily locked. Try again later.",
            )

        # Verify password
        if not verify_password(data.password, user.password_hash):
            await self._increment_failed_attempts(user)
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Reset failed attempts on success
        await self.redis.delete(failed_attempts_key(str(user.id)))

        # Generate and send OTP
        otp = generate_otp()
        await self.redis.setex(
            otp_redis_key(str(user.id)),
            settings.OTP_EXPIRE_SECONDS,
            otp,
        )

        # TODO: send email with OTP
        # In development, log OTP to console:
        print(f"[DEV] OTP for {user.email}: {otp}")

        await self.db.execute(
            AuditLog.__table__.insert().values(
                id=uuid.uuid4(), user_id=user.id,
                action="LOGIN_ATTEMPT", ip_address=ip
            )
        )
        await self.db.commit()
        return LoginStep1Response(email=data.email)

    # ─── Login Step 2: OTP verify → issue tokens ─────────────────────────────

    async def login_step2(self, data: OTPVerifyRequest, ip: str = None, user_agent: str = None) -> TokenResponse:
        user = await self._get_user_by_email(data.email)

        stored_otp = await self.redis.get(otp_redis_key(str(user.id)))
        if not stored_otp or stored_otp != data.otp_code:
            raise HTTPException(status_code=401, detail="Invalid or expired OTP code")

        await self.redis.delete(otp_redis_key(str(user.id)))

        return await self._issue_tokens(user, ip, user_agent)

    # ─── Refresh ─────────────────────────────────────────────────────────────

    async def refresh_tokens(self, refresh_token: str, ip: str = None) -> TokenResponse:
        try:
            payload = decode_token(refresh_token)
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Wrong token type")

        token_hash = _hash_token(refresh_token)
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.is_revoked == False,
            )
        )
        rt = result.scalar_one_or_none()
        if not rt or rt.expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="Refresh token expired or revoked")

        # Revoke old token
        rt.is_revoked = True
        await self.db.flush()

        user = await self.db.get(User, rt.user_id)
        return await self._issue_tokens(user, ip)

    # ─── Logout ──────────────────────────────────────────────────────────────

    async def logout(self, refresh_token: str) -> dict:
        token_hash = _hash_token(refresh_token)
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        rt = result.scalar_one_or_none()
        if rt:
            rt.is_revoked = True
            await self.db.commit()
        return {"message": "Logged out successfully"}

    # ─── Helpers ─────────────────────────────────────────────────────────────

    async def _get_user_by_email(self, email: str) -> User:
        result = await self.db.execute(select(User).where(User.email == email, User.is_active == True))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return user

    async def _issue_tokens(self, user: User, ip: str = None, user_agent: str = None) -> TokenResponse:
        access_token = create_access_token({"sub": str(user.id), "role": user.role.value})
        refresh_token = create_refresh_token({"sub": str(user.id)})

        # Store hashed refresh token
        expires = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        self.db.add(RefreshToken(
            user_id=user.id,
            token_hash=_hash_token(refresh_token),
            expires_at=expires,
            ip_address=ip,
            user_agent=user_agent,
        ))
        await self.db.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def _increment_failed_attempts(self, user: User):
        key = failed_attempts_key(str(user.id))
        attempts = await self.redis.incr(key)
        await self.redis.expire(key, 900)  # 15 min window
        if attempts >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
            await self.redis.setex(
                lockout_redis_key(str(user.id)),
                settings.LOCKOUT_DURATION_MINUTES * 60,
                "locked",
            )
