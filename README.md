# 🏥 MedLink UA — ЕМІС

**Електронна медична інформаційна система** для первинної ланки медичної допомоги.
Дипломна робота. Інтеграція з ЕСОЗ через Mock-сервер.

---

## ⚡ Швидкий старт (5 кроків)

### 1. Запустити інфраструктуру
```bash
docker compose up -d
```
PostgreSQL → `localhost:5432` | Redis → `localhost:6379` | MinIO → `localhost:9000`

### 2. Backend — налаштування
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

pip install -r requirements.txt
cp .env.example .env
# Відредагуйте .env — мінімум потрібен SECRET_KEY
```

### 3. Міграції БД
```bash
cd backend
alembic upgrade head
```

### 4. Запустити сервіси
```bash
# Термінал 1 — Backend API
cd backend
uvicorn app.main:app --reload --port 8000

# Термінал 2 — Mock ЕСОЗ
cd esoz-mock
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

### 5. Перевірити
| Сервіс | URL |
|--------|-----|
| Backend Swagger | http://localhost:8000/docs |
| Mock ЕСОЗ Swagger | http://localhost:8080/docs |
| MinIO Console | http://localhost:9001 (admin/minioadmin123) |

---

## 🏗️ Структура проекту

```
medlink-ua/
├── backend/          # FastAPI + SQLAlchemy + Alembic
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── auth.py              # Auth endpoints (8 маршрутів)
│   │   │   ├── patients.py          # Patients endpoints (10 маршрутів)
│   │   │   ├── encounters.py        # Encounters + ICD-10 (9 маршрутів)
│   │   │   ├── prescriptions.py     # E-рецепти + препарати (5 маршрутів)
│   │   │   ├── appointments.py      # Запис + лікарі + розклад (9 маршрутів)
│   │   │   ├── patient_cabinet.py   # Кабінет пацієнта /me (8 маршрутів)
│   │   │   ├── admin.py             # Адмін-панель /admin (6 маршрутів)
│   │   │   └── analytics.py         # Аналітика /analytics (5 маршрутів)
│   │   ├── core/                    # config, db, security, dependencies
│   │   ├── models/                  # SQLAlchemy ORM (всі таблиці)
│   │   ├── schemas/
│   │   │   ├── auth.py
│   │   │   ├── patients.py
│   │   │   ├── encounters.py
│   │   │   ├── prescriptions.py
│   │   │   ├── appointments.py
│   │   │   ├── patient_cabinet.py   # Схеми кабінету пацієнта
│   │   │   ├── admin.py             # Схеми адмін-панелі
│   │   │   └── analytics.py         # GroupBy enum + 5 response моделей
│   │   ├── services/
│   │   │   ├── auth_service.py
│   │   │   ├── patient_service.py
│   │   │   ├── encounter_service.py
│   │   │   ├── prescription_service.py
│   │   │   ├── appointment_service.py
│   │   │   ├── patient_cabinet_service.py  # Кабінет пацієнта + MinIO аватари
│   │   │   ├── admin_service.py            # Управління юзерами + статистика
│   │   │   ├── analytics_service.py        # 5 метрик (date_trunc, FILTER WHERE)
│   │   │   └── esoz_connector.py
│   │   └── workers/
│   │       ├── celery_app.py
│   │       └── email_tasks.py
│   ├── scripts/
│   │   ├── import_icd10.py
│   │   └── import_drugs.py
│   ├── templates/
│   │   └── encounter_pdf.html
│   └── alembic/
├── esoz-mock/        # Mock ЕСОЗ API (порт 8080)
├── frontend/         # React 18 + TypeScript (порт 3000, placeholder)
└── docker-compose.yml
```

## 📋 Модулі (стан реалізації)

### Backend — повністю реалізовано ✅
| Модуль | Опис | Статус |
|--------|------|--------|
| **Модуль 1** | Авторизація + JWT + 2FA + скидання пароля | ✅ Done |
| **Модуль 2** | Пацієнти + ЕМК + алергії + хронічні хвороби + MinIO | ✅ Done |
| **Модуль 3** | Прийом лікаря + МКБ-10 + WeasyPrint PDF + MinIO | ✅ Done |
| **Модуль 4** | Е-рецепт + Mock ЕСОЗ синхронізація (OAuth2) | ✅ Done |
| **Модуль 5** | Онлайн-запис + Redis lock + Celery нагадування | ✅ Done |
| **Модуль 6** | Кабінет пацієнта (профіль, аватар, ЕМК ro, записи) | ✅ Done |
| **Модуль 7** | Адмін-панель (юзери, audit log) + Аналітика (5 метрик) | ✅ Done |

### Що ще не реалізовано
| Компонент | Пріоритет | Деталі |
|-----------|-----------|--------|
| **Frontend** (React 18 + TypeScript) | 🔴 Критично | `frontend/src/` порожній — потрібен повний SPA |
| **Тести** (pytest, ≥60% coverage) | 🔴 Критично | `backend/tests/` не існує |
| **Email через SMTP** | 🟡 Важливо | OTP та нагадування виводяться в консоль, SMTP не налаштований |
| **Перевірка алергій** при рецепті | 🟡 Важливо | Попередження якщо МНН препарату збігається з алергеном |
| **Dockerfiles** | 🟢 Бонус | `backend/Dockerfile`, `frontend/Dockerfile` не створені |

---

## 🖥️ Frontend — що потрібно реалізувати

**Стек:** Vite + React 18 + TypeScript + React Router v6 + Zustand + axios + Tailwind CSS + shadcn/ui + Recharts

```bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install react-router-dom zustand axios @tanstack/react-query
npm install react-hook-form zod @hookform/resolvers
npm install recharts react-qr-code
npm install -D tailwindcss postcss autoprefixer
```

### Сторінки по ролях

**DOCTOR** (`/doctor/*`):
- `/doctor` — Дашборд: прийоми на сьогодні (GET /api/v1/appointments/today)
- `/doctor/patients` — Пошук пацієнтів
- `/doctor/patients/:id` — Карта пацієнта (вкладки: ЕМК, Прийоми, Рецепти, Документи)
- `/doctor/encounters/new` — Новий прийом (автозбереження кожні 30с, ICD-10 пошук, виписка рецепту)
- `/doctor/patients/new` — Реєстрація нового пацієнта

**PATIENT** (`/patient/*`):
- `/patient` — Дашборд: наступний запис, активні рецепти, останній прийом
- `/patient/profile` — Профіль + аватар + зміна пароля
- `/patient/medical-card` — ЕМК тільки для читання
- `/patient/encounters` — Мої прийоми + PDF завантаження
- `/patient/prescriptions` — Активні рецепти з QR-кодом (esoz_request_number)
- `/patient/appointments` — Мої записи + запис до лікаря (вибір лікаря → дата → слот)
- `/patient/documents` — Мої документи

**ADMIN** (`/admin/*`):
- `/admin` — Дашборд: stats cards + 4 графіки Recharts (аналітика)
- `/admin/users` — Таблиця користувачів (фільтри, пагінація)
- `/admin/users/:id` — Деталі юзера + деактивація + зміна ролі
- `/admin/audit-logs` — Журнал дій (фільтри: юзер, дія, дата)

**Auth** (публічні):
- `/login` → `/login/2fa` → (redirect by role)
- `/forgot-password` → `/reset-password?token=...`

---

## 🧪 Тести — що потрібно реалізувати

```
backend/tests/
├── conftest.py          # async client, test DB, fixtures (users, patients)
├── unit/
│   ├── test_auth_service.py        # register, login, OTP, lockout, refresh
│   ├── test_patient_service.py     # CRUD, duplicate tax_id, medical card
│   ├── test_encounter_service.py   # create, autosave, complete, ICD-10
│   ├── test_prescription_service.py # create + ЕСОЗ sync, cancel, allergy check
│   ├── test_appointment_service.py  # slots, booking, double-book, cancel
│   └── test_analytics_service.py   # 5 метрик з date range
└── integration/
    ├── test_auth_api.py            # повний 2FA flow через HTTP
    ├── test_esoz_integration.py    # prescription → Mock ЕСОЗ → esoz_request_number
    ├── test_admin_api.py           # CRUD юзерів, audit log
    └── test_patient_cabinet_api.py # PATIENT role: own data only
```

```bash
cd backend
pytest --cov=app --cov-report=html -v
# результат: htmlcov/index.html (ціль ≥60%)
```

---

## 📧 Email — що потрібно налаштувати

OTP та нагадування зараз виводяться в консоль. Для реального email:
1. Встановити Mailtrap (dev) або Gmail App Password
2. Заповнити в `.env`: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`
3. Створити `backend/app/services/email_service.py` з методами `send_otp()`, `send_password_reset()`, `send_appointment_reminder()`
4. Замінити `print("DEV OTP:", otp)` в `auth_service.py` на виклик email service

---

## 🔑 Тест авторизації (curl)
```bash
# Реєстрація
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"doctor@test.com","password":"Test1234!","first_name":"Іван","last_name":"Лікаренко","role":"DOCTOR"}'

# Логін (отримати OTP в консолі uvicorn)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"doctor@test.com","password":"Test1234!"}'

# 2FA (замінити OTP з консолі)
curl -X POST http://localhost:8000/api/v1/auth/login/2fa \
  -H "Content-Type: application/json" \
  -d '{"email":"doctor@test.com","otp_code":"482931"}'

# Скидання пароля
curl -X POST http://localhost:8000/api/v1/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email":"doctor@test.com"}'

curl -X POST http://localhost:8000/api/v1/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{"token":"<токен з консолі>","new_password":"NewPass1234!"}'
```

## 🏥 Тест пацієнтів (curl)
```bash
TOKEN="eyJ..."

# Створити пацієнта
curl -X POST http://localhost:8000/api/v1/patients \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tax_id":"1234567890","first_name":"Олена","last_name":"Петренко","birth_date":"1985-06-15","gender":"FEMALE","phone":"+380991234567"}'

# Пошук пацієнтів
curl "http://localhost:8000/api/v1/patients?search=Петренко" \
  -H "Authorization: Bearer $TOKEN"

# Медична карта
curl http://localhost:8000/api/v1/patients/{id}/medical-card \
  -H "Authorization: Bearer $TOKEN"
```

## 👤 Тест кабінету пацієнта (curl)
```bash
PATIENT_TOKEN="eyJ..."   # токен пацієнта

# Профіль
curl http://localhost:8000/api/v1/me \
  -H "Authorization: Bearer $PATIENT_TOKEN"

# Оновити ПІБ/телефон
curl -X PATCH http://localhost:8000/api/v1/me \
  -H "Authorization: Bearer $PATIENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"phone":"+380991234567","first_name":"Олена"}'

# Завантажити аватар
curl -X POST http://localhost:8000/api/v1/me/avatar \
  -H "Authorization: Bearer $PATIENT_TOKEN" \
  -F "file=@/path/to/photo.jpg"

# Медична картка (тільки читання)
curl http://localhost:8000/api/v1/me/medical-card \
  -H "Authorization: Bearer $PATIENT_TOKEN"

# Історія прийомів
curl http://localhost:8000/api/v1/me/encounters \
  -H "Authorization: Bearer $PATIENT_TOKEN"

# Рецепти (тільки активні)
curl "http://localhost:8000/api/v1/me/prescriptions?status=ACTIVE" \
  -H "Authorization: Bearer $PATIENT_TOKEN"

# Змінити пароль
curl -X PATCH http://localhost:8000/api/v1/me/change-password \
  -H "Authorization: Bearer $PATIENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"current_password":"Test1234!","new_password":"NewPass1234!"}'
```

## 🛡️ Тест адмін-панелі (curl)
```bash
ADMIN_TOKEN="eyJ..."   # токен адміністратора

# Список користувачів (з фільтрами)
curl "http://localhost:8000/api/v1/admin/users?role=DOCTOR&is_active=true" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Деталі користувача + кількість audit-подій
curl http://localhost:8000/api/v1/admin/users/{id} \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Деактивувати користувача
curl -X POST http://localhost:8000/api/v1/admin/users/{id}/deactivate \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Журнал дій
curl "http://localhost:8000/api/v1/admin/audit-logs?action=LOGIN&limit=20" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Системна статистика
curl http://localhost:8000/api/v1/admin/stats \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

## 📊 Тест аналітики (curl)
```bash
TOKEN="eyJ..."   # токен ADMIN або DOCTOR

# Динаміка записів по місяцях
curl "http://localhost:8000/api/v1/analytics/appointments?group_by=month&date_from=2026-01-01" \
  -H "Authorization: Bearer $TOKEN"

# Топ-10 МКБ-10 діагнозів
curl "http://localhost:8000/api/v1/analytics/diagnoses/top10?date_from=2026-01-01" \
  -H "Authorization: Bearer $TOKEN"

# Навантаження лікарів
curl "http://localhost:8000/api/v1/analytics/doctors/load?date_from=2026-01-01" \
  -H "Authorization: Bearer $TOKEN"

# Відсоток скасувань
curl "http://localhost:8000/api/v1/analytics/appointments/cancellation-rate?date_from=2026-01-01" \
  -H "Authorization: Bearer $TOKEN"
```

## 🩺 Тест прийому лікаря (curl)
```bash
TOKEN="eyJ..."  # токен лікаря

# Створити прийом
curl -X POST http://localhost:8000/api/v1/encounters \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"patient_id":"<uuid>"}'

# Додати діагноз (МКБ-10)
curl -X POST http://localhost:8000/api/v1/encounters/<id>/diagnoses \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"icd10_id":"<uuid>","type":"MAIN"}'

# Завершити прийом
curl -X POST http://localhost:8000/api/v1/encounters/<id>/complete \
  -H "Authorization: Bearer $TOKEN"

# Отримати PDF виписку
curl http://localhost:8000/api/v1/encounters/<id>/pdf \
  -H "Authorization: Bearer $TOKEN" --output discharge.pdf
```

## 💊 Тест е-рецептів (curl)
```bash
# Виписати рецепт
curl -X POST http://localhost:8000/api/v1/prescriptions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"encounter_id":"<uuid>","drug_id":"<uuid>","dosage":"500мг","frequency":"2р/день","duration_days":7}'

# Пошук препаратів
curl "http://localhost:8000/api/v1/prescriptions/drugs/search?q=парацет" \
  -H "Authorization: Bearer $TOKEN"

# Скасувати рецепт
curl -X PATCH http://localhost:8000/api/v1/prescriptions/<id>/cancel \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason":"Замінено препарат"}'
```

## 📅 Тест онлайн-запису (curl)
```bash
# Список лікарів
curl http://localhost:8000/api/v1/doctors \
  -H "Authorization: Bearer $TOKEN"

# Вільні слоти
curl "http://localhost:8000/api/v1/doctors/<id>/slots?date=2026-04-01" \
  -H "Authorization: Bearer $TOKEN"

# Записатись (токен пацієнта)
PATIENT_TOKEN="eyJ..."
curl -X POST http://localhost:8000/api/v1/appointments \
  -H "Authorization: Bearer $PATIENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"doctor_id":"<uuid>","slot_datetime":"2026-04-01T09:00:00Z","reason":"Огляд"}'
```

## ⚙️ Celery воркер
```bash
cd backend
celery -A app.workers.celery_app worker --loglevel=info
```

## 📥 Імпорт довідників
```bash
# МКБ-10 (CSV: code,name_ua,name_en,category)
python scripts/import_icd10.py icd10.csv

# Препарати (CSV: atc_code,inn,trade_name,form,dosage,manufacturer)
python scripts/import_drugs.py drugs.csv
```
