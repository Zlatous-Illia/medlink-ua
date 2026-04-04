"""
Unit tests for AuthService.

Tests are isolated from HTTP layer — service methods are called directly.
Redis is replaced with FakeRedis; DB uses the medlink_test PostgreSQL database.
"""

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole, RefreshToken
from app.core.security import hash_password, verify_password
from app.schemas.auth import (
    UserRegisterRequest, UserLoginRequest, OTPVerifyRequest,
    ForgotPasswordRequest, ResetPasswordRequest,
)
from app.services.auth_service import AuthService
from tests.conftest import FakeRedis


# ─── Helpers ─────────────────────────────────────────────────────────────────

def make_service(db: AsyncSession, redis: FakeRedis) -> AuthService:
    return AuthService(db=db, redis=redis)


async def _create_user(
    db: AsyncSession,
    email: str = "user@test.com",
    password: str = "Secret1234!",
    role: UserRole = UserRole.PATIENT,
) -> User:
    user = User(
        email=email,
        password_hash=hash_password(password),
        role=role,
        first_name="Тест",
        last_name="Юзер",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# ─── Register ────────────────────────────────────────────────────────────────

class TestRegister:
    async def test_register_success(self, db_session, fake_redis):
        svc = make_service(db_session, fake_redis)
        req = UserRegisterRequest(
            email="newuser@test.com",
            password="NewUser1234!",
            first_name="Новий",
            last_name="Юзер",
            role=UserRole.PATIENT,
        )
        result = await svc.register(req)

        assert result.email == "newuser@test.com"
        assert result.role == UserRole.PATIENT
        assert result.first_name == "Новий"
        assert result.is_active is True

    async def test_register_creates_audit_log(self, db_session, fake_redis):
        from app.models.user import AuditLog
        svc = make_service(db_session, fake_redis)
        req = UserRegisterRequest(
            email="audit@test.com",
            password="Audit1234!",
            first_name="Аудит",
            last_name="Тест",
        )
        result = await svc.register(req)

        logs = (await db_session.execute(
            select(AuditLog).where(AuditLog.user_id == result.id)
        )).scalars().all()
        assert any(log.action == "REGISTER" for log in logs)

    async def test_register_duplicate_email_raises_400(self, db_session, fake_redis):
        await _create_user(db_session, email="dup@test.com")

        svc = make_service(db_session, fake_redis)
        req = UserRegisterRequest(
            email="dup@test.com",
            password="Another1234!",
            first_name="Другий",
            last_name="Юзер",
        )
        with pytest.raises(HTTPException) as exc_info:
            await svc.register(req)
        assert exc_info.value.status_code == 400
        assert "already registered" in exc_info.value.detail

    async def test_register_doctor_role(self, db_session, fake_redis):
        svc = make_service(db_session, fake_redis)
        req = UserRegisterRequest(
            email="doctor@test.com",
            password="Doctor1234!",
            first_name="Доктор",
            last_name="Тест",
            role=UserRole.DOCTOR,
        )
        result = await svc.register(req)
        assert result.role == UserRole.DOCTOR


# ─── Login Step 1 ─────────────────────────────────────────────────────────────

class TestLoginStep1:
    async def test_login_wrong_password_raises_401(self, db_session, fake_redis):
        await _create_user(db_session, email="login@test.com", password="Correct1234!")

        svc = make_service(db_session, fake_redis)
        req = UserLoginRequest(email="login@test.com", password="Wrong1234!")
        with pytest.raises(HTTPException) as exc_info:
            await svc.login_step1(req)
        assert exc_info.value.status_code == 401

    async def test_login_nonexistent_email_raises_401(self, db_session, fake_redis):
        svc = make_service(db_session, fake_redis)
        req = UserLoginRequest(email="nobody@test.com", password="Test1234!")
        with pytest.raises(HTTPException) as exc_info:
            await svc.login_step1(req)
        assert exc_info.value.status_code == 401

    async def test_login_success_stores_otp_in_redis(self, db_session, fake_redis):
        user = await _create_user(db_session, email="otp@test.com", password="Otp12345!")

        svc = make_service(db_session, fake_redis)
        req = UserLoginRequest(email="otp@test.com", password="Otp12345!")
        result = await svc.login_step1(req)

        assert result.email == "otp@test.com"
        assert result.requires_2fa is True

        otp_key = f"otp:{user.id}"
        stored_otp = await fake_redis.get(otp_key)
        assert stored_otp is not None
        assert len(stored_otp) == 6
        assert stored_otp.isdigit()

    async def test_login_locked_account_raises_429(self, db_session, fake_redis):
        user = await _create_user(db_session, email="locked@test.com", password="Lock1234!")

        # Simulate active lockout
        lockout_key = f"lockout:{user.id}"
        await fake_redis.setex(lockout_key, 900, "locked")

        svc = make_service(db_session, fake_redis)
        req = UserLoginRequest(email="locked@test.com", password="Lock1234!")
        with pytest.raises(HTTPException) as exc_info:
            await svc.login_step1(req)
        assert exc_info.value.status_code == 429

    async def test_lockout_after_5_failed_attempts(self, db_session, fake_redis):
        await _create_user(db_session, email="brute@test.com", password="Safe1234!")

        svc = make_service(db_session, fake_redis)
        req = UserLoginRequest(email="brute@test.com", password="WrongWrong1!")

        # 5 consecutive wrong passwords
        for _ in range(5):
            try:
                await svc.login_step1(req)
            except HTTPException:
                pass

        # 6th attempt should hit lockout
        with pytest.raises(HTTPException) as exc_info:
            await svc.login_step1(req)
        assert exc_info.value.status_code == 429

    async def test_failed_attempts_reset_on_success(self, db_session, fake_redis):
        user = await _create_user(db_session, email="reset@test.com", password="Reset1234!")

        svc = make_service(db_session, fake_redis)
        # One failed attempt
        try:
            await svc.login_step1(UserLoginRequest(email="reset@test.com", password="Wrong!"))
        except HTTPException:
            pass

        # Successful login should reset counter
        await svc.login_step1(UserLoginRequest(email="reset@test.com", password="Reset1234!"))

        failed_key = f"failed:{user.id}"
        assert await fake_redis.get(failed_key) is None


# ─── Login Step 2 (OTP verify) ───────────────────────────────────────────────

class TestLoginStep2:
    async def test_verify_correct_otp_returns_tokens(self, db_session, fake_redis):
        user = await _create_user(db_session, email="verify@test.com", password="Verify1234!")

        # Manually seed OTP in fake redis
        await fake_redis.setex(f"otp:{user.id}", 300, "123456")

        svc = make_service(db_session, fake_redis)
        req = OTPVerifyRequest(email="verify@test.com", otp_code="123456")
        result = await svc.login_step2(req)

        assert result.access_token is not None
        assert result.refresh_token is not None
        assert result.token_type == "bearer"
        assert result.expires_in > 0

    async def test_verify_stores_refresh_token_in_db(self, db_session, fake_redis):
        user = await _create_user(db_session, email="rt@test.com", password="Rt123456!")
        await fake_redis.setex(f"otp:{user.id}", 300, "654321")

        svc = make_service(db_session, fake_redis)
        await svc.login_step2(OTPVerifyRequest(email="rt@test.com", otp_code="654321"))

        tokens = (await db_session.execute(
            select(RefreshToken).where(RefreshToken.user_id == user.id)
        )).scalars().all()
        assert len(tokens) == 1
        assert tokens[0].is_revoked is False

    async def test_verify_wrong_otp_raises_401(self, db_session, fake_redis):
        user = await _create_user(db_session, email="wrong_otp@test.com", password="Wro1234!")
        await fake_redis.setex(f"otp:{user.id}", 300, "111111")

        svc = make_service(db_session, fake_redis)
        req = OTPVerifyRequest(email="wrong_otp@test.com", otp_code="999999")
        with pytest.raises(HTTPException) as exc_info:
            await svc.login_step2(req)
        assert exc_info.value.status_code == 401

    async def test_verify_expired_otp_raises_401(self, db_session, fake_redis):
        await _create_user(db_session, email="expired@test.com", password="Exp12345!")
        # Don't store any OTP — simulates expired / never stored

        svc = make_service(db_session, fake_redis)
        req = OTPVerifyRequest(email="expired@test.com", otp_code="000000")
        with pytest.raises(HTTPException) as exc_info:
            await svc.login_step2(req)
        assert exc_info.value.status_code == 401

    async def test_otp_deleted_from_redis_after_use(self, db_session, fake_redis):
        user = await _create_user(db_session, email="once@test.com", password="Once1234!")
        otp_key = f"otp:{user.id}"
        await fake_redis.setex(otp_key, 300, "777777")

        svc = make_service(db_session, fake_redis)
        await svc.login_step2(OTPVerifyRequest(email="once@test.com", otp_code="777777"))

        assert await fake_redis.get(otp_key) is None


# ─── Refresh Tokens ───────────────────────────────────────────────────────────

class TestRefreshTokens:
    async def test_refresh_returns_new_tokens(self, db_session, fake_redis):
        user = await _create_user(db_session, email="refresh@test.com", password="Ref12345!")
        await fake_redis.setex(f"otp:{user.id}", 300, "888888")

        svc = make_service(db_session, fake_redis)
        tokens = await svc.login_step2(
            OTPVerifyRequest(email="refresh@test.com", otp_code="888888")
        )

        result = await svc.refresh_tokens(tokens.refresh_token)
        assert result.access_token is not None
        assert result.refresh_token != tokens.refresh_token  # new token issued

    async def test_refresh_revokes_old_token(self, db_session, fake_redis):
        user = await _create_user(db_session, email="revoke@test.com", password="Rev12345!")
        await fake_redis.setex(f"otp:{user.id}", 300, "112233")

        svc = make_service(db_session, fake_redis)
        tokens = await svc.login_step2(
            OTPVerifyRequest(email="revoke@test.com", otp_code="112233")
        )
        old_rt = tokens.refresh_token
        await svc.refresh_tokens(old_rt)

        # Old token should be revoked in DB
        from app.services.auth_service import _hash_token
        rt_row = (await db_session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == _hash_token(old_rt))
        )).scalar_one_or_none()
        assert rt_row is not None
        assert rt_row.is_revoked is True

    async def test_refresh_with_invalid_token_raises_401(self, db_session, fake_redis):
        svc = make_service(db_session, fake_redis)
        with pytest.raises(HTTPException) as exc_info:
            await svc.refresh_tokens("not-a-valid-jwt-token")
        assert exc_info.value.status_code == 401


# ─── Logout ───────────────────────────────────────────────────────────────────

class TestLogout:
    async def test_logout_revokes_refresh_token(self, db_session, fake_redis):
        user = await _create_user(db_session, email="logout@test.com", password="Logout12!")
        await fake_redis.setex(f"otp:{user.id}", 300, "445566")

        svc = make_service(db_session, fake_redis)
        tokens = await svc.login_step2(
            OTPVerifyRequest(email="logout@test.com", otp_code="445566")
        )
        result = await svc.logout(tokens.refresh_token)

        assert result["message"] == "Logged out successfully"

        from app.services.auth_service import _hash_token
        rt_row = (await db_session.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == _hash_token(tokens.refresh_token)
            )
        )).scalar_one_or_none()
        assert rt_row is not None
        assert rt_row.is_revoked is True

    async def test_logout_with_unknown_token_is_noop(self, db_session, fake_redis):
        """Logout with an unknown token should not raise — just return success message."""
        svc = make_service(db_session, fake_redis)
        # Generate a valid JWT that's not stored in DB
        from app.core.security import create_refresh_token
        token = create_refresh_token({"sub": "00000000-0000-0000-0000-000000000000"})
        result = await svc.logout(token)
        assert "message" in result


# ─── Forgot / Reset Password ─────────────────────────────────────────────────

class TestPasswordReset:
    async def test_forgot_password_stores_reset_token(self, db_session, fake_redis):
        user = await _create_user(db_session, email="forgot@test.com", password="Forgot12!")

        svc = make_service(db_session, fake_redis)
        result = await svc.forgot_password(ForgotPasswordRequest(email="forgot@test.com"))

        assert "message" in result
        # At least one pwd_reset key should exist in fake redis
        reset_keys = [k for k in fake_redis._store if k.startswith("pwd_reset:")]
        assert len(reset_keys) == 1

    async def test_forgot_password_nonexistent_email_returns_same_message(
        self, db_session, fake_redis
    ):
        """Should NOT leak information about whether email exists."""
        svc = make_service(db_session, fake_redis)
        result = await svc.forgot_password(
            ForgotPasswordRequest(email="nobody@test.com")
        )
        assert "message" in result
        # No reset token stored
        reset_keys = [k for k in fake_redis._store if k.startswith("pwd_reset:")]
        assert len(reset_keys) == 0

    async def test_reset_password_success(self, db_session, fake_redis):
        user = await _create_user(db_session, email="reset_pw@test.com", password="OldPass1!")

        svc = make_service(db_session, fake_redis)
        await svc.forgot_password(ForgotPasswordRequest(email="reset_pw@test.com"))

        reset_key = next(k for k in fake_redis._store if k.startswith("pwd_reset:"))
        token = reset_key.replace("pwd_reset:", "")

        result = await svc.reset_password(
            ResetPasswordRequest(token=token, new_password="NewPass2!")
        )
        assert result["message"] == "Password has been reset successfully"

        # Verify password was actually changed
        await db_session.refresh(user)
        assert verify_password("NewPass2!", user.password_hash)
        assert not verify_password("OldPass1!", user.password_hash)

    async def test_reset_password_revokes_all_refresh_tokens(self, db_session, fake_redis):
        user = await _create_user(db_session, email="reset_rt@test.com", password="Old12345!")

        # Issue a refresh token
        await fake_redis.setex(f"otp:{user.id}", 300, "999111")
        svc = make_service(db_session, fake_redis)
        tokens = await svc.login_step2(
            OTPVerifyRequest(email="reset_rt@test.com", otp_code="999111")
        )

        # Reset password
        await svc.forgot_password(ForgotPasswordRequest(email="reset_rt@test.com"))
        reset_key = next(k for k in fake_redis._store if k.startswith("pwd_reset:"))
        token = reset_key.replace("pwd_reset:", "")
        await svc.reset_password(ResetPasswordRequest(token=token, new_password="New99999!"))

        # All refresh tokens should be revoked
        refresh_tokens = (await db_session.execute(
            select(RefreshToken).where(RefreshToken.user_id == user.id)
        )).scalars().all()
        assert all(rt.is_revoked for rt in refresh_tokens)

    async def test_reset_password_invalid_token_raises_400(self, db_session, fake_redis):
        svc = make_service(db_session, fake_redis)
        with pytest.raises(HTTPException) as exc_info:
            await svc.reset_password(
                ResetPasswordRequest(token="nonexistent-token", new_password="New1234!")
            )
        assert exc_info.value.status_code == 400
