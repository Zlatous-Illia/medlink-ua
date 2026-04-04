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
cp .env.example .env   # required keys: SECRET_KEY, DATABASE_URL, DATABASE_URL_SYNC
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

### Frontend
```bash
cd frontend
npm install
npm run dev    # http://localhost:5173
```

### URLs
| Service | URL |
|---------|-----|
| Frontend (React SPA) | http://localhost:5173 |
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

Alembic reads `DATABASE_URL` from `settings` (not `alembic.ini`). Both async (`DATABASE_URL`) and sync (`DATABASE_URL_SYNC`) URLs are required in `.env`.

## Testing

Tests live in `backend/tests/`. Requires `docker compose up -d` (uses a separate `medlink_test` DB).

```bash
cd backend
pytest -v                              # all 93 tests
pytest tests/unit/ -v                  # 47 unit tests
pytest tests/integration/ -v           # 46 integration tests
pytest --cov=app --cov-report=html -v  # with coverage → htmlcov/index.html
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
schemas/
  auth.py                — Auth request/response schemas
  patients.py            — Patient, MedicalCard, Allergy, ChronicDisease, Document schemas
  encounters.py          — Encounter, Diagnosis, ICD10Search schemas
  prescriptions.py       — Prescription, Drug schemas
  appointments.py        — Appointment, Doctor, Schedule, Slot schemas
  patient_cabinet.py     — Patient self-service schemas (UserProfileResponse, MyEncounterResponse, …)
  admin.py               — Admin schemas (UserAdminResponse, AuditLogResponse, SystemStatsResponse)
  analytics.py           — Analytics schemas (GroupBy enum, 5 response models)
services/
  auth_service.py              — AuthService (register, login 2FA, refresh, logout, password reset);
                                 sends OTP + reset emails via email_service; always prints to console
  patient_service.py           — PatientService (CRUD, medical card, document upload to MinIO)
  encounter_service.py         — EncounterService (CRUD, diagnoses, ICD-10 search, WeasyPrint PDF)
  prescription_service.py      — PrescriptionService (create+allergy check, cancel, drug search, ЕСОЗ sync)
  appointment_service.py       — AppointmentService (doctors, slots, booking, Celery reminders, schedule)
  patient_cabinet_service.py   — PatientCabinetService (profile, avatar, medical card RO, encounters,
                                 prescriptions, documents, change-password)
  admin_service.py             — AdminService (user management, audit logs, system stats)
  analytics_service.py         — AnalyticsService (5 metrics via date_trunc + FILTER WHERE)
  email_service.py             — EmailService (send_otp, send_password_reset, send_appointment_reminder);
                                 always prints to console; sends real email when SMTP credentials set
  esoz_connector.py            — ESOZConnector (OAuth2 + НСЗУ API calls)
api/v1/
  auth.py             — Auth router (registered)
  patients.py         — Patients router (registered)
  encounters.py       — Encounters router + icd10_router (registered)
  prescriptions.py    — Prescriptions router (registered)
  appointments.py     — Appointments router + doctors_router (registered)
  patient_cabinet.py  — Patient Cabinet router /me (registered)
  admin.py            — Admin router /admin (registered)
  analytics.py        — Analytics router /analytics (registered)
workers/
  celery_app.py    — Celery app (Redis broker/backend, timezone Europe/Kiev)
  email_tasks.py   — send_reminder task (24h/1h appointment reminders); prints + sends real email
templates/
  encounter_pdf.html — Jinja2 template for discharge sheet PDF (WeasyPrint)
```

### Implemented API Endpoints

Registered routers in `main.py`: `auth`, `patients`, `encounters`, `icd10_router`, `prescriptions`, `appointments`, `doctors_router`, `patient_cabinet`, `admin`, `analytics`.

**Auth** (`/api/v1/auth/`):
- `POST /register` — create new user
- `POST /login` — step 1: verify password, send OTP (printed to console + emailed)
- `POST /login/2fa` — step 2: verify OTP, issue JWT tokens
- `POST /refresh` — rotate refresh token
- `POST /logout` — revoke refresh token
- `GET /me` — current user profile (requires JWT)
- `POST /forgot-password` — generate reset token (printed to console + emailed)
- `POST /reset-password` — validate token, set new password, revoke all refresh tokens

**Patients** (`/api/v1/patients/`):
- `POST /` — create patient + empty medical card (DOCTOR, ADMIN)
- `GET /` — list patients with ILIKE search (DOCTOR, ADMIN)
- `GET /{id}` — get patient; PATIENT role restricted to own profile (DOCTOR, ADMIN, PATIENT)
- `PATCH /{id}` — partial update patient demographics (DOCTOR, ADMIN)
- `GET /{id}/medical-card` — get medical card + allergies + chronic diseases (DOCTOR)
- `PUT /{id}/medical-card` — update medical card fields (DOCTOR)
- `POST /{id}/allergies` — add allergy record (DOCTOR, ADMIN)
- `POST /{id}/chronic-diseases` — add chronic disease with ICD-10 link (DOCTOR)
- `POST /{id}/documents` — upload PDF/image to MinIO (DOCTOR, ADMIN)
- `GET /{id}/history` — encounter history with diagnoses (DOCTOR)

**Encounters** (`/api/v1/encounters/` + `/api/v1/icd10/`):
- `POST /encounters` — create encounter (DOCTOR)
- `GET /encounters/{id}` — get encounter (DOCTOR)
- `PATCH /encounters/{id}` — autosave update (DOCTOR)
- `POST /encounters/{id}/complete` — complete encounter (DOCTOR)
- `GET /encounters/{id}/pdf` — WeasyPrint discharge PDF → MinIO (DOCTOR, PATIENT)
- `POST /encounters/{id}/diagnoses` — add ICD-10 diagnosis (DOCTOR)
- `GET /encounters/patients/{id}/encounters` — patient encounter list (DOCTOR)
- `GET /appointments/today` — today's schedule (DOCTOR)
- `GET /icd10/search?q=&limit=` — search ICD-10 codes (DOCTOR)

**Prescriptions** (`/api/v1/prescriptions/`):
- `POST /` — create prescription; **allergy check → HTTP 409 if drug INN matches patient allergy** (DOCTOR)
- `GET /drugs/search?q=&limit=` — drug search (DOCTOR)
- `GET /patients/{id}/prescriptions` — patient prescriptions (DOCTOR, PATIENT)
- `GET /{id}` — get prescription (DOCTOR, PATIENT)
- `PATCH /{id}/cancel` — cancel prescription + ЕСОЗ cancel (DOCTOR)

**Patient Cabinet** (`/api/v1/me/`) — PATIENT only:
- `GET /` — own profile (User fields + patient_id if linked)
- `PATCH /` — update first_name, last_name, middle_name, phone (email не змінюється)
- `POST /avatar` — upload avatar JPEG/PNG ≤5 MB → MinIO medlink-avatars
- `GET /medical-card` — own medical card read-only (allergies, chronic diseases)
- `GET /encounters` — own encounter history with diagnoses + doctor name
- `GET /prescriptions?status=` — own prescriptions with drug details
- `GET /documents` — list of uploaded documents
- `PATCH /change-password` — change password + revoke all refresh tokens

**Admin** (`/api/v1/admin/`) — ADMIN, SUPER_ADMIN only:
- `GET /users` — list users (filters: role, is_active, search; paging)
- `GET /users/{id}` — user details + audit events count
- `PATCH /users/{id}` — change is_active / role (SUPER_ADMIN protected)
- `POST /users/{id}/deactivate` — deactivate + revoke all refresh tokens
- `GET /audit-logs` — audit journal (filters: user_id, action ILIKE, resource, date range)
- `GET /stats` — system stats: users by role, patients, encounters, prescriptions, appointments

**Analytics** (`/api/v1/analytics/`) — ADMIN, SUPER_ADMIN, DOCTOR (DOCTOR sees own data only):
- `GET /appointments?date_from&date_to&group_by=day|week|month` — appointments by period
- `GET /diagnoses/top10?date_from&date_to&doctor_id` — top-10 ICD-10 codes
- `GET /doctors/load?date_from&date_to` — doctor load (encounters + appointments count)
- `GET /prescriptions?date_from&date_to&group_by` — prescriptions by period
- `GET /appointments/cancellation-rate?date_from&date_to&doctor_id` — cancellation rate %

### Data Model Relationships

- `User` → optional `Patient` (1:1, via `Patient.user_id`) or `Doctor` (1:1, via `Doctor.user_id`)
- `Patient` → `MedicalCard` (1:1), `Allergy[]`, `ChronicDisease[]`, `PatientDocument[]`, `Appointment[]`
- `Doctor` → `Encounter[]`, `Schedule[]` (weekly recurring templates), `Appointment[]`
- `Encounter` → `Diagnosis[]`, `Prescription[]` (e-prescriptions), `Referral[]` (e-referrals)
- `Prescription` / `Referral` → have `esoz_*` fields populated after syncing to Mock ЕСОЗ
- Reference tables: `ICD10Code`, `Drug`, `Specialization`

### Auth Flow (2FA + Password Reset)

1. `POST /api/v1/auth/login` — verify password, generate OTP stored in Redis (`otp:{user_id}`); OTP always printed to console AND emailed via `email_service.send_otp()`
2. `POST /api/v1/auth/login/2fa` — verify OTP, issue JWT access token (15 min) + refresh token (7 days, hashed & stored in DB)
3. `POST /api/v1/auth/refresh` — rotate refresh token
4. Lockout: 5 failed attempts → 15 min lockout via Redis keys
5. `POST /api/v1/auth/forgot-password` — generate reset token (`pwd_reset:{token}` in Redis, TTL 1h); always printed to console AND emailed via `email_service.send_password_reset()`
6. `POST /api/v1/auth/reset-password` — validate token, update password hash, revoke all refresh tokens

Roles: `PATIENT`, `DOCTOR`, `ADMIN`, `SUPER_ADMIN`. Role guards: `require_doctor`, `require_admin` in `dependencies.py`.

### Allergy Check on Prescription Creation

In `prescription_service.py` → `create_prescription()`:
- After loading the drug, queries all patient allergies from DB
- Compares `drug.inn.lower()` against each `allergy.substance.lower()` (case-insensitive substring match in both directions)
- If a match is found: logs `[ALLERGY]` to console and raises `HTTP 409` with:
  ```json
  {"warning": "Drug INN matches patient allergy", "allergy": "...", "drug_inn": "...", "severity": "..."}
  ```
- Frontend should display as a dismissible warning (doctor can override by proceeding manually)

### Email Service (`email_service.py`)

Three async functions: `send_otp()`, `send_password_reset()`, `send_appointment_reminder()`.

**Dual output pattern** — always prints to console, then sends real email if SMTP configured:
```python
print(f"[DEV] OTP email → {email} | code: {otp}")   # always
await _send(subject, [email], body)                   # only when SMTP_USER + SMTP_PASSWORD set
```

**To enable real emails**, set in `backend/.env`:
```
SMTP_HOST=smtp.mailtrap.io   # or smtp.gmail.com
SMTP_PORT=2525               # mailtrap; use 587 for gmail
SMTP_USER=your_username
SMTP_PASSWORD=your_password
```
If `SMTP_USER` or `SMTP_PASSWORD` is empty → email silently skipped, no exception raised.

### Mock ЕСОЗ (`esoz-mock/app/`)

Simulates НСЗУ eHealth REST API. Routers: `oauth`, `persons`, `prescriptions`, `drugs`, `referrals`. No database — purely in-memory mock data.

The backend connects to it via `ESOZConnector` (`services/esoz_connector.py`) using OAuth2 client credentials flow.

### Infrastructure (docker-compose.yml)

- **PostgreSQL 16** — main database (`medlink:medlink_secret@localhost:5432/medlink`)
- **Redis 7** — OTP storage, login lockout, Celery broker/backend (databases 0/1/2)
- **MinIO** — file storage for patient documents and avatars (two buckets: `medlink-docs`, `medlink-avatars`)

### MinIO Storage

- **Documents** (`medlink-docs`): `PatientService.upload_document()`, key pattern `patients/{patient_id}/{uuid}_{filename}`
- **Avatars** (`medlink-avatars`): `PatientCabinetService.upload_avatar()`, key pattern `avatars/{user_id}/{uuid}_{filename}`, old avatar deleted on re-upload

Both use synchronous MinIO SDK wrapped in `asyncio.get_running_loop().run_in_executor()`.

### Analytics Implementation Notes

- `AnalyticsService` uses `func.date_trunc(group_by.value, column)` for period grouping
- Aggregate filters use `func.count(1).filter(Model.status == X)` → PostgreSQL `COUNT(1) FILTER (WHERE ...)`
- `GroupBy` enum: `day | week | month` → passed directly to `date_trunc`
- DOCTOR role auto-filtered: service calls `_get_doctor_id(user)` and adds `WHERE doctor_id = ...`
- Default date range: last 30 days if `date_from` not provided

### Frontend (`frontend/src/`)

React 18 + TypeScript + Vite SPA. Runs on port 5173 (`npm run dev`). Built output in `frontend/dist/`.

```
api/             — Axios client (JWT interceptor, auto-refresh on 401) + typed API modules + types.ts
store/           — authStore.ts (Zustand, localStorage persistence)
router/          — index.tsx (React Router v6, role-based PrivateRoute)
components/
  layout/        — AppShell.tsx (sidebar + topbar), Sidebar.tsx
  shared/        — Toast, LoadingSpinner, ConfirmDialog, StatusBadge, EmptyState
pages/
  auth/          — LoginPage, TwoFAPage, ForgotPasswordPage, ResetPasswordPage
  doctor/        — DoctorDashboard, PatientSearchPage, PatientDetailPage, NewEncounterPage, RegisterPatientPage
  patient/       — PatientDashboard, MyProfilePage, MyMedicalCardPage, MyEncountersPage,
                   MyPrescriptionsPage, MyAppointmentsPage, BookAppointmentPage, MyDocumentsPage
  admin/         — AdminDashboard, UsersListPage, UserDetailPage, AuditLogPage
```

## Key Conventions

- All DB operations are **async** (SQLAlchemy asyncio + asyncpg driver). Use `await session.execute(select(...))` pattern.
- New routers go in `backend/app/api/v1/` and must be registered in `backend/app/main.py`.
- New models must be imported in `backend/app/models/__init__.py` so Alembic autogenerate detects them.
- Forward reference imports (to break circular imports) go at the **bottom** of model files.
- Pydantic schemas use `model_validate()` (v2 API), not `from_orm()`.
- `AuditLog` entries should be added for significant actions.
- Email functions always print to console for dev visibility — do not remove the `print()` calls.

---

## Implementation Status & Roadmap

### What is already implemented

| Component | Status |
|-----------|--------|
| Docker Compose (PostgreSQL, Redis, MinIO) | ✅ Done |
| FastAPI app structure + settings | ✅ Done |
| All SQLAlchemy ORM models (all groups) | ✅ Done |
| Alembic migration (initial tables) | ✅ Done |
| **Module 1 — Auth** (register, login 2FA, refresh, logout, me, forgot/reset password) | ✅ Done |
| Mock ЕСОЗ server (oauth, persons, prescriptions, drugs, referrals) | ✅ Done |
| **Module 2 — Patients & EMK** (CRUD, medical card, allergies, chronic diseases, documents, history) | ✅ Done |
| **Module 3 — Encounters** (create/update/complete, diagnoses, ICD-10 search, WeasyPrint PDF, MinIO storage) | ✅ Done |
| **Module 4 — E-Prescription** (create+allergy check, cancel, drug search, ЕСОЗ sync via `ESOZConnector`) | ✅ Done |
| **Module 5 — Appointments** (doctor list, slot generation, Redis optimistic lock, Celery 24h/1h reminders, schedule CRUD) | ✅ Done |
| **Module 6 — Patient Cabinet** (profile, avatar MinIO, medical card RO, encounters, prescriptions, documents, change-password) | ✅ Done |
| **Module 7 — Admin Panel** (user management, audit log journal, system stats) | ✅ Done |
| **Module 7 — Analytics** (5 metrics: appointments by period, top-10 ICD-10, doctor load, prescriptions, cancellation rate) | ✅ Done |
| **Email service** (OTP, password reset, appointment reminders via fastapi-mail; always prints to console) | ✅ Done |
| **Allergy check** (HTTP 409 when drug INN matches patient allergy on prescription creation) | ✅ Done |
| ICD-10 & Drug import scripts (`scripts/import_icd10.py`, `scripts/import_drugs.py`) | ✅ Done |
| **Frontend — React SPA** (21 pages: auth, doctor workspace, patient cabinet, admin panel) | ✅ Done |
| **Tests — Auth** (unit: 25 tests for AuthService; integration: 25 tests for Auth API) | ✅ Done |
| **Tests — Patients** (unit: 22 tests for PatientService; integration: 21 tests for Patient Cabinet API) | ✅ Done |

### Frontend — Implemented (`frontend/src/`)

**Stack:** Vite + React 18 + TypeScript, React Router v6, Zustand (authStore with localStorage), Axios (JWT interceptor + auto-refresh), Tailwind CSS, React Hook Form + Zod, Recharts (charts), react-qr-code.

**Run:**
```bash
cd frontend
npm install
npm run dev    # http://localhost:5173
npm run build  # production build → dist/
```

**Module F1 — Auth pages** (`src/pages/auth/`): `LoginPage.tsx`, `TwoFAPage.tsx`, `ForgotPasswordPage.tsx`, `ResetPasswordPage.tsx`

**Module F2 — Doctor workspace** (`src/pages/doctor/`): `DoctorDashboard.tsx`, `PatientSearchPage.tsx`, `PatientDetailPage.tsx` (tabs: ЕМК, Прийоми, Рецепти, Документи), `NewEncounterPage.tsx` (autosave 30s, ICD-10 search, inline prescription form), `RegisterPatientPage.tsx`

**Module F3 — Patient cabinet** (`src/pages/patient/`): `PatientDashboard.tsx`, `MyProfilePage.tsx` (avatar upload), `MyMedicalCardPage.tsx`, `MyEncountersPage.tsx`, `MyPrescriptionsPage.tsx` (QR codes), `MyAppointmentsPage.tsx`, `BookAppointmentPage.tsx` (doctor → date → slot), `MyDocumentsPage.tsx`

**Module F4 — Admin panel** (`src/pages/admin/`): `AdminDashboard.tsx` (stats + 4 Recharts charts), `UsersListPage.tsx`, `UserDetailPage.tsx`, `AuditLogPage.tsx`

**Shared:** `AppShell.tsx` + `Sidebar.tsx` (role-based nav), `Toast.tsx`, `LoadingSpinner.tsx`, `ConfirmDialog.tsx`, `StatusBadge.tsx`

**API client** (`src/api/`): `client.ts` (axios + Bearer token interceptor + 401 auto-refresh), `types.ts` (TypeScript interfaces for all backend schemas), plus typed modules: `auth.ts`, `patients.ts`, `encounters.ts`, `prescriptions.ts`, `appointments.ts`, `patientCabinet.ts`, `admin.ts`, `analytics.ts`

### Tests — Implemented (`backend/tests/`)

**Infrastructure:** `pytest.ini` (asyncio_mode=auto), `conftest.py` (FakeRedis, test engine → `medlink_test` PostgreSQL, `clean_db` autouse truncation, user/patient fixtures).

**Run (requires `docker compose up -d` first):**
```bash
cd backend
pytest -v                              # all 93 tests
pytest tests/unit/ -v                  # 47 unit tests
pytest tests/integration/ -v           # 46 integration tests
pytest --cov=app --cov-report=html -v  # with coverage → htmlcov/index.html
```

**Already written (93 tests):**

| File | Tests | Coverage |
|------|-------|---------|
| `unit/test_auth_service.py` | 25 | register, login, lockout, OTP, refresh, logout, pwd reset |
| `unit/test_patient_service.py` | 22 | create, search, access control, update, allergies, medical card |
| `integration/test_auth_api.py` | 25 | full 2FA flow, refresh, logout, /me, forgot/reset password |
| `integration/test_patient_cabinet_api.py` | 21 | GET/PATCH /me, medical card, encounters, prescriptions, change-password |

### What is NOT yet implemented (TODO)

#### REMAINING TESTS

**Missing unit tests** (`backend/tests/unit/`):
- `test_encounter_service.py` — create encounter, autosave PATCH, complete, add diagnosis, ICD-10 search
- `test_prescription_service.py` — create prescription (ЕСОЗ sync mock), cancel, drug search, allergy 409 warning
- `test_appointment_service.py` — slot generation, booking (Redis lock), double-booking prevention, cancel
- `test_analytics_service.py` — 5 metrics with date range params

**Missing integration tests** (`backend/tests/integration/`):
- `test_esoz_integration.py` — prescription creation → Mock ЕСОЗ sync → `esoz_request_number` populated
- `test_admin_api.py` — user CRUD, audit log filtering, stats endpoint

#### DOCKERFILES (optional, for deployment demo)

- `backend/Dockerfile` — FROM python:3.11-slim, COPY requirements.txt, RUN pip install, COPY app/, CMD uvicorn
- `esoz-mock/Dockerfile` — same pattern
- `frontend/Dockerfile` — FROM node:20-alpine, npm ci, npm run build, serve via nginx:alpine

### API Endpoints by Module

**Module 2 — Patients:** ✅ Implemented (`api/v1/patients.py`)
```
POST   /api/v1/patients                           DOCTOR, ADMIN
GET    /api/v1/patients                           DOCTOR, ADMIN  (search: name, tax_id, phone)
GET    /api/v1/patients/{id}                      DOCTOR, ADMIN, PATIENT(own)
PATCH  /api/v1/patients/{id}                      DOCTOR, ADMIN
GET    /api/v1/patients/{id}/medical-card         DOCTOR
PUT    /api/v1/patients/{id}/medical-card         DOCTOR
POST   /api/v1/patients/{id}/allergies            DOCTOR, ADMIN
POST   /api/v1/patients/{id}/chronic-diseases     DOCTOR
POST   /api/v1/patients/{id}/documents            DOCTOR, ADMIN  (upload to MinIO)
GET    /api/v1/patients/{id}/history              DOCTOR         (all encounters)
```

**Module 3 — Encounters:** ✅ Implemented (`api/v1/encounters.py`)
```
GET    /api/v1/appointments/today                     DOCTOR (today's schedule)
POST   /api/v1/encounters                             DOCTOR
GET    /api/v1/encounters/{id}                        DOCTOR
PATCH  /api/v1/encounters/{id}                        DOCTOR (autosave)
POST   /api/v1/encounters/{id}/complete               DOCTOR
GET    /api/v1/encounters/{id}/pdf                    DOCTOR, PATIENT  (WeasyPrint → MinIO)
POST   /api/v1/encounters/{id}/diagnoses              DOCTOR
GET    /api/v1/encounters/patients/{id}/encounters    DOCTOR
GET    /api/v1/icd10/search?q=&limit=                 DOCTOR
```

**Module 4 — Prescriptions:** ✅ Implemented (`api/v1/prescriptions.py`)
```
POST   /api/v1/prescriptions                              DOCTOR  (+ allergy check + ЕСОЗ sync)
GET    /api/v1/prescriptions/drugs/search?q=&limit=       DOCTOR
GET    /api/v1/prescriptions/patients/{id}/prescriptions  DOCTOR, PATIENT
GET    /api/v1/prescriptions/{id}                         DOCTOR, PATIENT
PATCH  /api/v1/prescriptions/{id}/cancel                  DOCTOR  (+ ЕСОЗ cancel)
```

**Module 5 — Appointments:** ✅ Implemented (`api/v1/appointments.py`)
```
GET    /api/v1/appointments/today              DOCTOR
GET    /api/v1/appointments                    DOCTOR, PATIENT
POST   /api/v1/appointments                    PATIENT  (Redis lock + Celery reminders)
GET    /api/v1/appointments/{id}               DOCTOR, PATIENT
PATCH  /api/v1/appointments/{id}/cancel        DOCTOR, PATIENT
GET    /api/v1/doctors                         ALL
GET    /api/v1/doctors/{id}/slots?date=        ALL
POST   /api/v1/doctors/{id}/schedule           ADMIN
GET    /api/v1/doctors/{id}/schedule           ALL
```

**Module 6 — Patient Cabinet:** ✅ Implemented (`api/v1/patient_cabinet.py`)
```
GET    /api/v1/me                              PATIENT
PATCH  /api/v1/me                              PATIENT
POST   /api/v1/me/avatar                       PATIENT  (JPEG/PNG ≤5MB → MinIO medlink-avatars)
GET    /api/v1/me/medical-card                 PATIENT  (read-only)
GET    /api/v1/me/encounters                   PATIENT
GET    /api/v1/me/prescriptions?status=        PATIENT
GET    /api/v1/me/documents                    PATIENT
PATCH  /api/v1/me/change-password              PATIENT
```

**Module 7 — Admin Panel:** ✅ Implemented (`api/v1/admin.py`)
```
GET    /api/v1/admin/users                     ADMIN, SUPER_ADMIN
GET    /api/v1/admin/users/{id}                ADMIN, SUPER_ADMIN
PATCH  /api/v1/admin/users/{id}                ADMIN, SUPER_ADMIN
POST   /api/v1/admin/users/{id}/deactivate     ADMIN, SUPER_ADMIN
GET    /api/v1/admin/audit-logs                ADMIN, SUPER_ADMIN
GET    /api/v1/admin/stats                     ADMIN, SUPER_ADMIN
```

**Module 7 — Analytics:** ✅ Implemented (`api/v1/analytics.py`)
```
GET    /api/v1/analytics/appointments                   ADMIN, SUPER_ADMIN, DOCTOR
GET    /api/v1/analytics/diagnoses/top10                ADMIN, SUPER_ADMIN, DOCTOR
GET    /api/v1/analytics/doctors/load                   ADMIN, SUPER_ADMIN, DOCTOR
GET    /api/v1/analytics/prescriptions                  ADMIN, SUPER_ADMIN, DOCTOR
GET    /api/v1/analytics/appointments/cancellation-rate ADMIN, SUPER_ADMIN, DOCTOR
```

### DB Schema Key Points

- All PKs are UUID (`gen_random_uuid()`)
- Soft delete via `is_active` (no physical deletes of medical data)
- Personal data (`patients`) stored separately from medical data (`medical_cards`) — ЕСОЗ requirement
- `esoz_person_id` on `patients` — populated after Mock ЕСОЗ `/api/persons` verification
- `esoz_request_id` + `esoz_request_number` on `prescriptions` — populated after Mock ЕСОЗ sync
- `audit_log` actions: LOGIN, VIEW_EMR, CREATE_PRESCRIPTION, CANCEL_PRESCRIPTION, UPLOAD_DOCUMENT, CREATE_ENCOUNTER, COMPLETE_ENCOUNTER, GENERATE_PDF, CREATE_APPOINTMENT, CANCEL_APPOINTMENT, VIEW_PROFILE, UPDATE_PROFILE, UPLOAD_AVATAR, VIEW_MEDICAL_CARD, VIEW_ENCOUNTERS, VIEW_PRESCRIPTIONS, CHANGE_PASSWORD, ADMIN_UPDATE_USER
