# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**MedLink UA** — an Electronic Medical Information System (ЕМІС) for primary healthcare, a diploma project integrating with the Ukrainian national eHealth system (ЕСОЗ) via a mock server.

Two FastAPI services:
- **Backend** (`backend/`, port 8000) — main API with PostgreSQL, Redis, MinIO
- **Mock ЕСОЗ** (`esoz-mock/`, port 8080) — simulates the Ukrainian national eHealth (НСЗУ) API

## Running the Services

### Prerequisites
```bash
# Start infrastructure (PostgreSQL, Redis, MinIO)
docker compose up -d
```

### Backend
```bash
cd backend
cp .env.example .env   # edit SECRET_KEY at minimum
pip install -r requirements.txt
alembic upgrade head   # run DB migrations
uvicorn app.main:app --reload --port 8000
```

### Mock ЕСОЗ
```bash
cd esoz-mock
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

### URLs
| Service | URL |
|---------|-----|
| Backend Swagger | http://localhost:8000/docs |
| Mock ЕСОЗ Swagger | http://localhost:8080/docs |
| MinIO Console | http://localhost:9001 (admin/minioadmin123) |

## Database Migrations (Alembic)

All commands run from `backend/`:
```bash
alembic upgrade head              # apply all migrations
alembic revision --autogenerate -m "description"  # create new migration
alembic downgrade -1              # rollback one step
```

Alembic reads `DATABASE_URL` from `settings` (not `alembic.ini`). Both async and sync URLs are required in `.env`.

## Testing
```bash
cd backend
pytest                            # run all tests
pytest tests/test_auth.py         # run single file
pytest -v -k "test_login"         # run matching tests
```

## Architecture

### Backend (`backend/app/`)

```
core/
  config.py       — pydantic-settings Settings class; all config loaded from .env
  database.py     — async SQLAlchemy engine, Base, get_db() dependency
  security.py     — password hashing, JWT creation/decode, OTP generation, Redis key helpers
  dependencies.py — FastAPI dependencies: get_redis(), get_current_user(), require_roles()
models/           — SQLAlchemy ORM models (all imported via app/models/__init__.py)
schemas/          — Pydantic v2 request/response models
services/         — business logic (AuthService, ESOZConnector)
api/v1/           — FastAPI routers; each router instantiates a Service class
```

### Data Model Relationships

- `User` → optional `Patient` (1:1) or `Doctor` (1:1)
- `Patient` → `MedicalCard` (1:1), `Allergy[]`, `ChronicDisease[]`, `PatientDocument[]`
- `Doctor` → `Encounter[]` (doctor visits)
- `Encounter` → `Diagnosis[]`, `Prescription[]` (e-prescriptions), `Referral[]` (e-referrals)
- `Prescription` / `Referral` → have `esoz_*` fields populated after syncing to Mock ЕСОЗ
- Reference tables: `ICD10Code`, `Drug`, `Specialization`

### Auth Flow (2FA)

1. `POST /api/v1/auth/login` — verify password, generate OTP stored in Redis (`otp:{user_id}`), log OTP to console in dev
2. `POST /api/v1/auth/login/2fa` — verify OTP, issue JWT access token (15 min) + refresh token (7 days, hashed & stored in DB)
3. `POST /api/v1/auth/refresh` — rotate refresh token
4. Lockout: 5 failed attempts → 15 min lockout via Redis keys

Roles: `PATIENT`, `DOCTOR`, `ADMIN`, `SUPER_ADMIN`. Role guards: `require_doctor`, `require_admin` in `dependencies.py`.

### Mock ЕСОЗ (`esoz-mock/app/`)

Simulates НСЗУ eHealth REST API. Routers: `oauth`, `persons`, `prescriptions`, `drugs`, `referrals`. No database — purely in-memory mock data.

The backend connects to it via `ESOZConnector` (`services/esoz_connector.py`) using OAuth2 client credentials flow.

### Infrastructure (docker-compose.yml)

- **PostgreSQL 16** — main database (`medlink:medlink_secret@localhost:5432/medlink`)
- **Redis 7** — OTP storage, login lockout, Celery broker/backend
- **MinIO** — file storage for patient documents and avatars (two buckets: `medlink-docs`, `medlink-avatars`)

## Key Conventions

- All DB operations are **async** (SQLAlchemy asyncio + asyncpg driver). Use `await session.execute(select(...))` pattern.
- New routers go in `backend/app/api/v1/` and must be registered in `backend/app/main.py`.
- New models must be imported in `backend/app/models/__init__.py` so Alembic autogenerate detects them.
- Forward reference imports (to break circular imports) go at the **bottom** of model files.
- Pydantic schemas use `model_validate()` (v2 API), not `from_orm()`.
- `AuditLog` entries should be added for significant actions.