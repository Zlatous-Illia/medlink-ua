"""
Integration tests for the Auth API endpoints.

Uses httpx AsyncClient against the full FastAPI application with:
- test PostgreSQL database (medlink_test)
- FakeRedis for OTP / lockout storage

Covers the complete 2FA login flow end-to-end.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole, RefreshToken
from app.core.security import hash_password
from tests.conftest import FakeRedis, TestSessionFactory, make_token


BASE = "/api/v1/auth"


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def _create_user_in_db(
    email: str,
    password: str = "Test1234!",
    role: UserRole = UserRole.PATIENT,
) -> User:
    async with TestSessionFactory() as session:
        user = User(
            email=email,
            password_hash=hash_password(password),
            role=role,
            first_name="Тест",
            last_name="Інтеграція",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


# ─── Register endpoint ────────────────────────────────────────────────────────

class TestRegisterEndpoint:
    async def test_register_returns_201(self, async_client: AsyncClient):
        resp = await async_client.post(f"{BASE}/register", json={
            "email": "new@integration.com",
            "password": "NewUser1234!",
            "first_name": "Новий",
            "last_name": "Юзер",
            "role": "PATIENT",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "new@integration.com"
        assert data["role"] == "PATIENT"
        assert "password" not in data
        assert "password_hash" not in data

    async def test_register_returns_user_id(self, async_client: AsyncClient):
        resp = await async_client.post(f"{BASE}/register", json={
            "email": "withid@integration.com",
            "password": "WithId1234!",
            "first_name": "З",
            "last_name": "Ід",
        })
        assert resp.status_code == 201
        assert "id" in resp.json()

    async def test_register_duplicate_email_returns_400(self, async_client: AsyncClient):
        payload = {
            "email": "dup@integration.com",
            "password": "Dup12345!",
            "first_name": "Перший",
            "last_name": "Реєстрація",
        }
        await async_client.post(f"{BASE}/register", json=payload)

        resp = await async_client.post(f"{BASE}/register", json=payload)
        assert resp.status_code == 400

    async def test_register_weak_password_returns_422(self, async_client: AsyncClient):
        # No uppercase letter
        resp = await async_client.post(f"{BASE}/register", json={
            "email": "weak@integration.com",
            "password": "alllowercase1",
            "first_name": "Слабкий",
            "last_name": "Пароль",
        })
        assert resp.status_code == 422

    async def test_register_no_digit_password_returns_422(self, async_client: AsyncClient):
        # No digit
        resp = await async_client.post(f"{BASE}/register", json={
            "email": "nodigit@integration.com",
            "password": "NoDigitPassword",
            "first_name": "Без",
            "last_name": "Цифри",
        })
        assert resp.status_code == 422

    async def test_register_doctor_role(self, async_client: AsyncClient):
        resp = await async_client.post(f"{BASE}/register", json={
            "email": "doc@integration.com",
            "password": "Doctor1234!",
            "first_name": "Доктор",
            "last_name": "Тест",
            "role": "DOCTOR",
        })
        assert resp.status_code == 201
        assert resp.json()["role"] == "DOCTOR"


# ─── Login Step 1 ─────────────────────────────────────────────────────────────

class TestLoginEndpoint:
    async def test_login_returns_email_and_2fa_flag(
        self, async_client: AsyncClient, fake_redis: FakeRedis
    ):
        await _create_user_in_db("login1@integration.com", "Login1234!")
        resp = await async_client.post(f"{BASE}/login", json={
            "email": "login1@integration.com",
            "password": "Login1234!",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "login1@integration.com"
        assert data["requires_2fa"] is True

    async def test_login_wrong_password_returns_401(self, async_client: AsyncClient):
        await _create_user_in_db("login2@integration.com", "Correct1234!")
        resp = await async_client.post(f"{BASE}/login", json={
            "email": "login2@integration.com",
            "password": "Wrong1234!",
        })
        assert resp.status_code == 401

    async def test_login_nonexistent_email_returns_401(self, async_client: AsyncClient):
        resp = await async_client.post(f"{BASE}/login", json={
            "email": "nobody@integration.com",
            "password": "Nobody1234!",
        })
        assert resp.status_code == 401

    async def test_login_stores_otp_in_redis(
        self, async_client: AsyncClient, fake_redis: FakeRedis
    ):
        user = await _create_user_in_db("otp_store@integration.com", "Otp12345!")
        await async_client.post(f"{BASE}/login", json={
            "email": "otp_store@integration.com",
            "password": "Otp12345!",
        })

        otp_keys = [k for k in fake_redis._store if k.startswith("otp:")]
        assert len(otp_keys) == 1


# ─── Login Step 2 (2FA) ───────────────────────────────────────────────────────

class TestTwoFAEndpoint:
    async def test_2fa_returns_access_and_refresh_tokens(
        self, async_client: AsyncClient, fake_redis: FakeRedis
    ):
        user = await _create_user_in_db("twofa@integration.com", "TwoFa1234!")
        await fake_redis.setex(f"otp:{user.id}", 300, "123456")

        resp = await async_client.post(f"{BASE}/login/2fa", json={
            "email": "twofa@integration.com",
            "otp_code": "123456",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    async def test_2fa_wrong_otp_returns_401(
        self, async_client: AsyncClient, fake_redis: FakeRedis
    ):
        user = await _create_user_in_db("twofa_wrong@integration.com", "TwoFa1234!")
        await fake_redis.setex(f"otp:{user.id}", 300, "111111")

        resp = await async_client.post(f"{BASE}/login/2fa", json={
            "email": "twofa_wrong@integration.com",
            "otp_code": "999999",
        })
        assert resp.status_code == 401

    async def test_2fa_expired_otp_returns_401(
        self, async_client: AsyncClient, fake_redis: FakeRedis
    ):
        await _create_user_in_db("twofa_expired@integration.com", "Exp12345!")
        # No OTP stored

        resp = await async_client.post(f"{BASE}/login/2fa", json={
            "email": "twofa_expired@integration.com",
            "otp_code": "000000",
        })
        assert resp.status_code == 401


# ─── Full 2FA flow ────────────────────────────────────────────────────────────

class TestFull2FAFlow:
    async def test_complete_login_flow(
        self, async_client: AsyncClient, fake_redis: FakeRedis
    ):
        """Register → Login → get OTP from redis → 2FA → tokens."""
        # Step 1: register
        reg_resp = await async_client.post(f"{BASE}/register", json={
            "email": "full_flow@integration.com",
            "password": "FullFlow1!",
            "first_name": "Повний",
            "last_name": "Флоу",
            "role": "DOCTOR",
        })
        assert reg_resp.status_code == 201
        user_id = reg_resp.json()["id"]

        # Step 2: login step 1
        login_resp = await async_client.post(f"{BASE}/login", json={
            "email": "full_flow@integration.com",
            "password": "FullFlow1!",
        })
        assert login_resp.status_code == 200

        # Step 3: get OTP from fake redis
        otp = fake_redis._store.get(f"otp:{user_id}")
        assert otp is not None

        # Step 4: verify OTP
        token_resp = await async_client.post(f"{BASE}/login/2fa", json={
            "email": "full_flow@integration.com",
            "otp_code": otp,
        })
        assert token_resp.status_code == 200
        tokens = token_resp.json()
        assert "access_token" in tokens

    async def test_access_token_allows_get_me(
        self, async_client: AsyncClient, fake_redis: FakeRedis
    ):
        """After full login flow, /me endpoint should return user info."""
        # Register
        reg = await async_client.post(f"{BASE}/register", json={
            "email": "getme@integration.com",
            "password": "GetMe1234!",
            "first_name": "Я",
            "last_name": "Тест",
        })
        user_id = reg.json()["id"]

        # Login
        await async_client.post(f"{BASE}/login", json={
            "email": "getme@integration.com",
            "password": "GetMe1234!",
        })
        otp = fake_redis._store.get(f"otp:{user_id}")

        token_resp = await async_client.post(f"{BASE}/login/2fa", json={
            "email": "getme@integration.com",
            "otp_code": otp,
        })
        access_token = token_resp.json()["access_token"]

        # /me
        me_resp = await async_client.get(
            f"{BASE}/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == "getme@integration.com"


# ─── GET /me ─────────────────────────────────────────────────────────────────

class TestGetMe:
    async def test_get_me_returns_user_profile(
        self, async_client: AsyncClient
    ):
        user = await _create_user_in_db("me@integration.com", role=UserRole.DOCTOR)
        token = make_token(user)

        resp = await async_client.get(
            f"{BASE}/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "me@integration.com"
        assert data["role"] == "DOCTOR"

    async def test_get_me_without_token_returns_403(self, async_client: AsyncClient):
        resp = await async_client.get(f"{BASE}/me")
        assert resp.status_code in (401, 403)

    async def test_get_me_with_invalid_token_returns_401(self, async_client: AsyncClient):
        resp = await async_client.get(
            f"{BASE}/me",
            headers={"Authorization": "Bearer totally-invalid-token"},
        )
        assert resp.status_code == 401


# ─── Refresh & Logout ────────────────────────────────────────────────────────

class TestRefreshAndLogout:
    async def test_refresh_returns_new_tokens(
        self, async_client: AsyncClient, fake_redis: FakeRedis
    ):
        user = await _create_user_in_db("refresh_int@integration.com", "Ref12345!")
        await fake_redis.setex(f"otp:{user.id}", 300, "222333")

        token_resp = await async_client.post(f"{BASE}/login/2fa", json={
            "email": "refresh_int@integration.com",
            "otp_code": "222333",
        })
        tokens = token_resp.json()
        old_access = tokens["access_token"]

        refresh_resp = await async_client.post(f"{BASE}/refresh", json={
            "refresh_token": tokens["refresh_token"],
        })
        assert refresh_resp.status_code == 200
        new_tokens = refresh_resp.json()
        assert new_tokens["access_token"] != old_access

    async def test_logout_returns_success_message(
        self, async_client: AsyncClient, fake_redis: FakeRedis
    ):
        user = await _create_user_in_db("logout_int@integration.com", "Logout12!")
        await fake_redis.setex(f"otp:{user.id}", 300, "444555")

        token_resp = await async_client.post(f"{BASE}/login/2fa", json={
            "email": "logout_int@integration.com",
            "otp_code": "444555",
        })
        refresh_token = token_resp.json()["refresh_token"]

        logout_resp = await async_client.post(f"{BASE}/logout", json={
            "refresh_token": refresh_token,
        })
        assert logout_resp.status_code == 200
        assert "message" in logout_resp.json()

    async def test_refresh_after_logout_returns_401(
        self, async_client: AsyncClient, fake_redis: FakeRedis
    ):
        user = await _create_user_in_db("logout2_int@integration.com", "Logout22!")
        await fake_redis.setex(f"otp:{user.id}", 300, "666777")

        token_resp = await async_client.post(f"{BASE}/login/2fa", json={
            "email": "logout2_int@integration.com",
            "otp_code": "666777",
        })
        refresh_token = token_resp.json()["refresh_token"]

        await async_client.post(f"{BASE}/logout", json={"refresh_token": refresh_token})

        resp = await async_client.post(f"{BASE}/refresh", json={"refresh_token": refresh_token})
        assert resp.status_code == 401


# ─── Forgot / Reset Password ─────────────────────────────────────────────────

class TestPasswordResetEndpoints:
    async def test_forgot_password_returns_safe_message(self, async_client: AsyncClient):
        await _create_user_in_db("forgot_ep@integration.com", "Forgot12!")
        resp = await async_client.post(f"{BASE}/forgot-password", json={
            "email": "forgot_ep@integration.com",
        })
        assert resp.status_code == 200
        assert "message" in resp.json()

    async def test_forgot_password_nonexistent_email_same_response(
        self, async_client: AsyncClient
    ):
        """Must not reveal whether email exists."""
        resp = await async_client.post(f"{BASE}/forgot-password", json={
            "email": "nonexistent@integration.com",
        })
        assert resp.status_code == 200
        assert "message" in resp.json()

    async def test_reset_password_with_valid_token(
        self, async_client: AsyncClient, fake_redis: FakeRedis
    ):
        user = await _create_user_in_db("reset_ep@integration.com", "OldPass1!")

        # Trigger forgot password to store token
        await async_client.post(f"{BASE}/forgot-password", json={
            "email": "reset_ep@integration.com",
        })
        reset_key = next(k for k in fake_redis._store if k.startswith("pwd_reset:"))
        token = reset_key.replace("pwd_reset:", "")

        resp = await async_client.post(f"{BASE}/reset-password", json={
            "token": token,
            "new_password": "NewPass2!",
        })
        assert resp.status_code == 200
        assert "message" in resp.json()

    async def test_reset_password_invalid_token_returns_400(self, async_client: AsyncClient):
        resp = await async_client.post(f"{BASE}/reset-password", json={
            "token": "fake-token-that-does-not-exist",
            "new_password": "NewPass2!",
        })
        assert resp.status_code == 400
