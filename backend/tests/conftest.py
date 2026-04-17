"""
Test configuration and fixtures for MedLink UA backend.

Uses a separate `medlink_test` PostgreSQL database.
Redis is replaced with an in-memory FakeRedis.
All tables are truncated after each test for isolation.
"""

import os
import sys
import asyncio
import pytest
import pytest_asyncio

# ─── Windows: switch to SelectorEventLoop so asyncpg teardown works ──────────
# ProactorEventLoop (default on Win32) sets _proactor=None on close, which
# causes asyncpg to raise AttributeError when flushing ROLLBACK on teardown.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from datetime import date
from typing import AsyncGenerator

# ─── Set env vars BEFORE importing any app module ────────────────────────────
# pydantic-settings gives higher priority to env vars than .env file.
os.environ["DATABASE_URL"] = (
    "postgresql+asyncpg://medlink:medlink_secret@localhost:5432/medlink_test"
)
os.environ["DATABASE_URL_SYNC"] = (
    "postgresql+psycopg2://medlink:medlink_secret@localhost:5432/medlink_test"
)
os.environ["SECRET_KEY"] = "test-secret-key-for-tests-only-32-characters!!"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"
os.environ["DEBUG"] = "false"

# ─── Create test database (synchronous, runs once at import time) ─────────────
def _create_test_database() -> None:
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            user="medlink",
            password="medlink_secret",
            database="postgres",
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        try:
            cur.execute("CREATE DATABASE medlink_test")
            print("\n[conftest] Created database: medlink_test")
        except psycopg2.errors.DuplicateDatabase:
            pass  # Already exists — fine
        finally:
            cur.close()
            conn.close()
    except Exception as e:
        print(f"\n[conftest] WARNING: Could not create test database: {e}")
        print("[conftest] Make sure PostgreSQL is running (docker compose up -d)")


_create_test_database()

# ─── Now safe to import app modules ───────────────────────────────────────────
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from httpx import AsyncClient, ASGITransport

import app.models  # noqa: F401 — register all models with Base.metadata
from app.main import app
from app.core.database import Base, get_db
from app.core.dependencies import get_redis
from app.core.security import hash_password, create_access_token
from app.models.user import User, UserRole
from app.models.patient import Patient, MedicalCard, Gender

# ─── Test engine pointing at medlink_test ────────────────────────────────────
TEST_DATABASE_URL = os.environ["DATABASE_URL"]
TEST_DATABASE_URL_SYNC = os.environ["DATABASE_URL_SYNC"]

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
TestSessionFactory = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


# ─── Create tables synchronously once at import time ─────────────────────────
def _create_tables() -> None:
    """Drop and recreate all tables in medlink_test using sync engine."""
    try:
        sync_engine = create_engine(TEST_DATABASE_URL_SYNC, echo=False)
        Base.metadata.drop_all(sync_engine)
        Base.metadata.create_all(sync_engine)
        sync_engine.dispose()
        print("\n[conftest] Tables created in medlink_test")
    except Exception as e:
        print(f"\n[conftest] WARNING: Could not create tables: {e}")


_create_tables()


# ─── FakeRedis ────────────────────────────────────────────────────────────────

class FakeRedis:
    """In-memory Redis substitute for unit and integration tests."""

    def __init__(self):
        self._store: dict = {}

    async def get(self, key: str):
        return self._store.get(key)

    async def set(self, key: str, value, nx: bool = False, ex: int = None, **kwargs):
        if nx and key in self._store:
            return None
        self._store[key] = str(value)
        return True

    async def setex(self, key: str, ttl: int, value):
        self._store[key] = str(value)
        return True

    async def delete(self, *keys: str):
        count = sum(1 for k in keys if self._store.pop(k, None) is not None)
        return count

    async def incr(self, key: str) -> int:
        val = int(self._store.get(key, 0)) + 1
        self._store[key] = str(val)
        return val

    async def expire(self, key: str, ttl: int):
        return 1

    async def aclose(self):
        pass

    def clear(self):
        self._store.clear()


# ─── Function-scoped: truncate tables after each test ────────────────────────

@pytest_asyncio.fixture(autouse=True)
async def clean_db():
    """Truncate all tables after each test to ensure full isolation."""
    yield
    async with test_engine.begin() as conn:
        await conn.execute(text("SET session_replication_role = replica"))
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())
        await conn.execute(text("SET session_replication_role = DEFAULT"))


# ─── Database session fixture ─────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an AsyncSession for unit tests (uses test engine).

    Uses explicit close with error suppression to avoid Windows-specific
    asyncpg teardown issues (ProactorEventLoop / asyncio loop-closed errors).
    """
    session = TestSessionFactory()
    try:
        yield session
    finally:
        try:
            await session.close()
        except Exception:
            pass


# ─── Fake Redis fixture ───────────────────────────────────────────────────────

@pytest.fixture
def fake_redis() -> FakeRedis:
    """Provide a fresh FakeRedis instance per test."""
    return FakeRedis()


# ─── HTTP client fixture ──────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def async_client(fake_redis: FakeRedis) -> AsyncGenerator[AsyncClient, None]:
    """
    HTTP test client with dependency overrides:
    - get_db  → session from test engine
    - get_redis → FakeRedis instance
    """

    async def override_get_db():
        async with TestSessionFactory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def override_get_redis():
        yield fake_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client

    app.dependency_overrides.clear()


# ─── User fixtures ────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def doctor_user(db_session: AsyncSession) -> User:
    user = User(
        email="doctor@medlink-test.com",
        password_hash=hash_password("Doctor1234!"),
        role=UserRole.DOCTOR,
        first_name="Іван",
        last_name="Лікаренко",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def patient_user(db_session: AsyncSession) -> User:
    user = User(
        email="patient@medlink-test.com",
        password_hash=hash_password("Patient1234!"),
        role=UserRole.PATIENT,
        first_name="Олена",
        last_name="Пацієнтова",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    user = User(
        email="admin@medlink-test.com",
        password_hash=hash_password("Admin1234!"),
        role=UserRole.ADMIN,
        first_name="Адмін",
        last_name="Системний",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def patient_profile(db_session: AsyncSession, patient_user: User) -> Patient:
    """Create a Patient record linked to patient_user, with an empty MedicalCard."""
    patient = Patient(
        user_id=patient_user.id,
        tax_id="9876543210",
        first_name="Олена",
        last_name="Пацієнтова",
        birth_date=date(1990, 5, 20),
        gender=Gender.FEMALE,
        phone="+380991234567",
    )
    db_session.add(patient)
    await db_session.flush()

    card = MedicalCard(patient_id=patient.id)
    db_session.add(card)
    await db_session.commit()
    await db_session.refresh(patient)
    return patient


# ─── Token helpers ────────────────────────────────────────────────────────────

def make_token(user: User) -> str:
    """Generate a valid JWT access token for a given user."""
    return create_access_token({"sub": str(user.id), "role": user.role.value})
