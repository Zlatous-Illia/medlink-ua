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

Alembic reads `DATABASE_URL` from `settings` (not `alembic.ini`). Both async (`DATABASE_URL`) and sync (`DATABASE_URL_SYNC`) URLs are required in `.env`.

## Testing

The `tests/` directory does not exist yet — create it under `backend/tests/` when writing tests:
```bash
cd backend
pytest                            # run all tests
pytest tests/test_auth.py         # run single file
pytest -v -k "test_login"         # run matching tests
```

Test infrastructure is already in `requirements.txt`: `pytest`, `pytest-asyncio`, `httpx`, `factory-boy`.

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
  auth_service.py              — AuthService (register, login 2FA, refresh, logout, password reset)
  patient_service.py           — PatientService (CRUD, medical card, document upload to MinIO)
  encounter_service.py         — EncounterService (CRUD, diagnoses, ICD-10 search, WeasyPrint PDF)
  prescription_service.py      — PrescriptionService (create, cancel, drug search, ЕСОЗ sync)
  appointment_service.py       — AppointmentService (doctors, slots, booking, Celery reminders, schedule)
  patient_cabinet_service.py   — PatientCabinetService (profile, avatar, medical card RO, encounters, prescriptions, documents, change-password)
  admin_service.py             — AdminService (user management, audit logs, system stats)
  analytics_service.py         — AnalyticsService (5 metrics via date_trunc + FILTER WHERE)
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
  email_tasks.py   — send_reminder task (24h/1h appointment reminders)
templates/
  encounter_pdf.html — Jinja2 template for discharge sheet PDF (WeasyPrint)
```

### Implemented API Endpoints

Registered routers in `main.py`: `auth`, `patients`, `encounters`, `icd10_router`, `prescriptions`, `appointments`, `doctors_router`, `patient_cabinet`, `admin`, `analytics`.

**Auth** (`/api/v1/auth/`):
- `POST /register` — create new user
- `POST /login` — step 1: verify password, send OTP
- `POST /login/2fa` — step 2: verify OTP, issue JWT tokens
- `POST /refresh` — rotate refresh token
- `POST /logout` — revoke refresh token
- `GET /me` — current user profile (requires JWT)
- `POST /forgot-password` — generate reset token (stored in Redis, TTL 1h; printed to console in dev)
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

1. `POST /api/v1/auth/login` — verify password, generate OTP stored in Redis (`otp:{user_id}`), log OTP to console in dev
2. `POST /api/v1/auth/login/2fa` — verify OTP, issue JWT access token (15 min) + refresh token (7 days, hashed & stored in DB)
3. `POST /api/v1/auth/refresh` — rotate refresh token
4. Lockout: 5 failed attempts → 15 min lockout via Redis keys
5. `POST /api/v1/auth/forgot-password` — generate reset token (`pwd_reset:{token}` in Redis, TTL 1h), print to console in dev
6. `POST /api/v1/auth/reset-password` — validate token, update password hash, revoke all refresh tokens

Roles: `PATIENT`, `DOCTOR`, `ADMIN`, `SUPER_ADMIN`. Role guards: `require_doctor`, `require_admin` in `dependencies.py`.

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

### Dependencies Not Yet Wired Up

These packages are in `requirements.txt` but have no full implementation yet:
- **fastapi-mail** — email sending (SMTP config keys exist in `config.py` but are empty; `send_reminder` task prints to console in DEBUG mode)

### Frontend

`frontend/src/` is a placeholder directory. No frontend framework is set up yet.

## Key Conventions

- All DB operations are **async** (SQLAlchemy asyncio + asyncpg driver). Use `await session.execute(select(...))` pattern.
- New routers go in `backend/app/api/v1/` and must be registered in `backend/app/main.py`.
- New models must be imported in `backend/app/models/__init__.py` so Alembic autogenerate detects them.
- Forward reference imports (to break circular imports) go at the **bottom** of model files.
- Pydantic schemas use `model_validate()` (v2 API), not `from_orm()`.
- `AuditLog` entries should be added for significant actions.

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
| **Module 4 — E-Prescription** (create, cancel, drug search, ЕСОЗ sync via `ESOZConnector`) | ✅ Done |
| **Module 5 — Appointments** (doctor list, slot generation, Redis optimistic lock, Celery 24h/1h reminders, schedule CRUD) | ✅ Done |
| **Module 6 — Patient Cabinet** (profile, avatar MinIO, medical card RO, encounters, prescriptions, documents, change-password) | ✅ Done |
| **Module 7 — Admin Panel** (user management, audit log journal, system stats) | ✅ Done |
| **Module 7 — Analytics** (5 metrics: appointments by period, top-10 ICD-10, doctor load, prescriptions, cancellation rate) | ✅ Done |
| ICD-10 & Drug import scripts (`scripts/import_icd10.py`, `scripts/import_drugs.py`) | ✅ Done |

### What is NOT yet implemented (TODO)

---

#### FRONTEND — React 18 + TypeScript (placeholder only, `frontend/src/` is empty)

**Stack to use:** Vite + React 18 + TypeScript, React Router v6, Zustand (state), axios (API client), Tailwind CSS + shadcn/ui, React Hook Form + Zod, Recharts (charts), react-qr-code (QR).

**Project init:**
```bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install react-router-dom zustand axios @tanstack/react-query
npm install react-hook-form zod @hookform/resolvers
npm install recharts react-qr-code
npm install -D tailwindcss postcss autoprefixer @types/node
npx tailwindcss init -p
# install shadcn/ui components as needed
```

**Module F1 — Auth pages** (`src/pages/auth/`):
- `LoginPage.tsx` — email + password form → POST /api/v1/auth/login
- `TwoFAPage.tsx` — 6-digit OTP input → POST /api/v1/auth/login/2fa; auto-redirect by role (DOCTOR→/doctor, PATIENT→/patient, ADMIN→/admin)
- `ForgotPasswordPage.tsx` — email → POST /api/v1/auth/forgot-password
- `ResetPasswordPage.tsx` — token from URL + new password → POST /api/v1/auth/reset-password
- Auth state in Zustand store: `{ user, accessToken, refreshToken, isAuthenticated }`
- Axios interceptor: attach Bearer token, on 401 call POST /api/v1/auth/refresh, retry original request
- Protected `<PrivateRoute role="DOCTOR|PATIENT|ADMIN">` HOC using React Router

**Module F2 — Doctor workspace** (`src/pages/doctor/`):
- `DoctorDashboard.tsx` — today's appointments list (GET /api/v1/appointments/today); shows patient name, time, reason, status badge
- `PatientSearchPage.tsx` — search bar (GET /api/v1/patients?search=...), patient cards list
- `PatientDetailPage.tsx` — patient demographics + tabs: [ЕМК | Прийоми | Рецепти | Документи]
  - ЕМК tab: blood type, allergies, chronic diseases (read + add buttons)
  - Прийоми tab: encounter history list (GET /api/v1/patients/{id}/history)
  - Рецепти tab: prescriptions list (GET /api/v1/prescriptions/patients/{id}/prescriptions)
  - Документи tab: document list with download links (GET /api/v1/patients/{id} → documents array)
- `NewEncounterPage.tsx` — start encounter form (POST /api/v1/encounters); fields: complaints, anamnesis, objective_exam, treatment_plan, recommendations; autosave every 30s via PATCH /api/v1/encounters/{id}; ICD-10 search combobox (GET /api/v1/icd10/search?q=); add diagnosis button; complete button (POST /api/v1/encounters/{id}/complete); download PDF button (GET /api/v1/encounters/{id}/pdf)
- `PrescriptionForm.tsx` (inline in encounter) — drug search combobox (GET /api/v1/prescriptions/drugs/search?q=), dosage, frequency, duration_days fields; POST /api/v1/prescriptions; shows allergy warning if drug INN matches patient allergy substance
- `RegisterPatientPage.tsx` — full patient registration form (POST /api/v1/patients): tax_id, first/last/middle name, birth_date, gender, phone, email, address fields

**Module F3 — Patient cabinet** (`src/pages/patient/`):
- `PatientDashboard.tsx` — 3 cards: next appointment, active prescriptions count, last encounter date
- `MyProfilePage.tsx` — profile form (GET/PATCH /api/v1/me); avatar upload (POST /api/v1/me/avatar) with preview; change password section (PATCH /api/v1/me/change-password)
- `MyMedicalCardPage.tsx` — read-only: blood type, allergies list, chronic diseases list (GET /api/v1/me/medical-card)
- `MyEncountersPage.tsx` — encounter cards with diagnoses; PDF download link per encounter (GET /api/v1/me/encounters)
- `MyPrescriptionsPage.tsx` — tabs: Active / All; each prescription shows drug name, dosage, QR code via `react-qr-code` (value = esoz_request_number); GET /api/v1/me/prescriptions?status=ACTIVE
- `MyAppointmentsPage.tsx` — upcoming + past appointments; cancel button (PATCH /api/v1/appointments/{id}/cancel) for upcoming; (GET /api/v1/me → appointments)
- `BookAppointmentPage.tsx` — doctor list (GET /api/v1/doctors), speciality filter; select doctor → date picker → slots grid (GET /api/v1/doctors/{id}/slots?date=); confirm booking (POST /api/v1/appointments)
- `MyDocumentsPage.tsx` — document cards with download URLs (GET /api/v1/me/documents)

**Module F4 — Admin panel** (`src/pages/admin/`):
- `AdminDashboard.tsx` — stats cards (GET /api/v1/admin/stats): users by role, total patients, encounters, prescriptions; + 4 analytics charts (Recharts LineChart/BarChart):
  - Appointments by month (GET /api/v1/analytics/appointments?group_by=month)
  - Top-10 diagnoses BarChart (GET /api/v1/analytics/diagnoses/top10)
  - Doctor load BarChart (GET /api/v1/analytics/doctors/load)
  - Cancellation rate LineChart (GET /api/v1/analytics/appointments/cancellation-rate)
- `UsersListPage.tsx` — table with filters: role, is_active, search; pagination (GET /api/v1/admin/users)
- `UserDetailPage.tsx` — user details + activate/deactivate toggle + role change dropdown (PATCH /api/v1/admin/users/{id}); audit events count
- `AuditLogPage.tsx` — filterable table: user, action, resource, date range (GET /api/v1/admin/audit-logs); server-side pagination

**Shared components** (`src/components/`):
- `Layout/` — `AppShell.tsx` with sidebar nav (role-based menu), topbar with user avatar + logout
- `UI/` — Button, Input, Select, Badge, Modal, Spinner (wrap shadcn/ui or build simple)
- `DataTable.tsx` — generic sortable/paginated table
- `DateRangePicker.tsx` — for analytics filters
- `QRCodeCard.tsx` — prescription QR wrapper

**API client** (`src/api/`):
- `client.ts` — axios instance with baseURL=`http://localhost:8000`, interceptors for auth + token refresh
- `auth.ts`, `patients.ts`, `encounters.ts`, `prescriptions.ts`, `appointments.ts`, `admin.ts`, `analytics.ts` — typed API functions matching all backend endpoints
- `types.ts` — TypeScript interfaces matching backend Pydantic schemas

**State management** (`src/store/`):
- `authStore.ts` — Zustand: user, tokens, login/logout actions, token persistence in localStorage
- `uiStore.ts` — loading states, toast notifications

**Routing** (`src/router/`):
- `index.tsx` — React Router v6: public routes (login, 2fa, forgot/reset password) + private routes grouped by role (doctor/*, patient/*, admin/*)

---

#### TESTS — pytest (backend/tests/ does not exist)

**Target: ≥60% code coverage.**

**Setup files to create:**
- `backend/tests/__init__.py`
- `backend/tests/conftest.py` — async test client, test DB session (SQLite in-memory or test PG), Redis mock, fixtures for test users (doctor, patient, admin)

**Unit tests** (`backend/tests/unit/`):
- `test_auth_service.py` — register, login (wrong password, lockout), OTP verify, refresh, logout, forgot/reset password
- `test_patient_service.py` — create patient, duplicate tax_id, search, medical card update, allergy add
- `test_encounter_service.py` — create encounter, autosave PATCH, complete, add diagnosis, ICD-10 search
- `test_prescription_service.py` — create prescription (with ЕСОЗ sync mock), cancel, drug search, allergy warning
- `test_appointment_service.py` — slot generation, booking (Redis lock), double-booking prevention, cancel (2h rule)
- `test_analytics_service.py` — each of 5 metrics with date range params

**Integration tests** (`backend/tests/integration/`):
- `test_auth_api.py` — full 2FA login flow via HTTP, token refresh, logout
- `test_esoz_integration.py` — prescription creation → Mock ЕСОЗ sync → esoz_request_number populated
- `test_admin_api.py` — user CRUD, audit log filtering, stats endpoint
- `test_patient_cabinet_api.py` — PATIENT role: own profile, medical card read-only, prescriptions

**Run:**
```bash
cd backend
pytest --cov=app --cov-report=html -v   # coverage report in htmlcov/
```

---

#### EMAIL — fastapi-mail (currently console-only)

**Files to update when implementing:**
- `backend/.env` — set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD (gmail app password or Mailtrap for dev)
- `backend/app/core/config.py` — SMTP settings already declared
- `backend/app/services/auth_service.py` — replace `print("DEV OTP:", otp)` with `await send_otp_email(user.email, otp)` via fastapi-mail
- `backend/app/workers/email_tasks.py` — replace `print()` with actual `FastMail.send_message()` call
- Create `backend/app/services/email_service.py` — `EmailService` with `send_otp()`, `send_password_reset()`, `send_appointment_reminder()` methods

**For dev/testing use Mailtrap** (`smtp.mailtrap.io:2525`) — free inbox, no real emails sent.

---

#### ALLERGY CHECK on prescription creation

- In `backend/app/services/prescription_service.py`, when creating a prescription, load patient's allergies and check if `drug.inn.lower()` matches any `allergy.substance.lower()`
- If match found, raise `HTTPException(status_code=409, detail={"warning": "Drug INN matches patient allergy", "allergy": allergy.substance})`
- Frontend should display this as a dismissible warning modal, not hard block (doctor can override)

---

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
POST   /api/v1/prescriptions                              DOCTOR  (+ ЕСОЗ sync)
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
