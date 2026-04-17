# MedLink UA — ЕМІС

**Електронна медична інформаційна система** для первинної ланки медичної допомоги.
Дипломна робота. Інтеграція з ЕСОЗ через Mock-сервер.

---

## Швидкий старт

### Варіант A — Повний Docker-стек (одна команда)
```bash
docker compose up -d --build
```
Піднімає все: PostgreSQL, Redis, MinIO, esoz-mock, backend, frontend.

> Після першого запуску потрібно виконати міграції:
> ```bash
> docker compose exec backend alembic upgrade head
> ```

### Варіант B — Локальна розробка

#### 1. Інфраструктура
```bash
docker compose up -d postgres redis minio
```

#### 2. Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

pip install -r requirements.txt
cp .env.example .env
# Відредагуйте .env — потрібен SECRET_KEY, DATABASE_URL, DATABASE_URL_SYNC

alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

#### 3. Mock ЕСОЗ
```bash
cd esoz-mock
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

#### 4. Frontend
```bash
cd frontend
npm install
npm run dev
```

### Доступні сервіси
| Сервіс | URL |
|--------|-----|
| Frontend (React SPA) | http://localhost:5173 |
| Backend Swagger | http://localhost:8000/docs |
| Mock ЕСОЗ Swagger | http://localhost:8080/docs |
| MinIO Console | http://localhost:9001 (admin/minioadmin123) |

---

## Структура проекту

```
medlink-ua/
├── backend/          # FastAPI + SQLAlchemy + Alembic (порт 8000)
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── auth.py              # Auth (8 маршрутів)
│   │   │   ├── patients.py          # Пацієнти (10 маршрутів)
│   │   │   ├── encounters.py        # Прийоми + ICD-10 (9 маршрутів)
│   │   │   ├── prescriptions.py     # Е-рецепти + препарати (5 маршрутів)
│   │   │   ├── appointments.py      # Записи + лікарі + розклад (9 маршрутів)
│   │   │   ├── patient_cabinet.py   # Кабінет пацієнта /me (8 маршрутів)
│   │   │   ├── admin.py             # Адмін-панель /admin (6 маршрутів)
│   │   │   └── analytics.py         # Аналітика /analytics (5 маршрутів)
│   │   ├── core/                    # config, db, security, dependencies
│   │   ├── models/                  # SQLAlchemy ORM (всі таблиці)
│   │   ├── schemas/                 # Pydantic v2 схеми (8 файлів)
│   │   ├── services/                # Бізнес-логіка (10 сервісів)
│   │   └── workers/                 # Celery задачі (нагадування)
│   ├── scripts/                     # import_icd10.py, import_drugs.py
│   ├── templates/                   # encounter_pdf.html (WeasyPrint)
│   ├── tests/                       # 93 тести (unit + integration)
│   └── alembic/                     # Міграції БД
├── esoz-mock/        # Mock ЕСОЗ API (порт 8080)
│   └── app/routers/  # oauth, persons, prescriptions, drugs, referrals
├── frontend/         # React 18 + TypeScript + Vite (порт 5173)
│   └── src/
│       ├── api/      # Axios client + типізовані API функції (10 модулів)
│       ├── pages/    # 21 сторінка (auth, doctor, patient, admin)
│       ├── components/ # Layout + shared UI компоненти
│       ├── store/    # Zustand (authStore)
│       └── router/   # React Router v6 (role-based routes)
└── docker-compose.yml
```

## Стан реалізації

### Повністю реалізовано
| Компонент | Опис | Статус |
|-----------|------|--------|
| **Модуль 1** | Авторизація + JWT + 2FA + скидання пароля | ✅ Done |
| **Модуль 2** | Пацієнти + ЕМК + алергії + хронічні хвороби + MinIO | ✅ Done |
| **Модуль 3** | Прийом лікаря + МКБ-10 + WeasyPrint PDF + MinIO | ✅ Done |
| **Е-направлення** | Створення направлення + ЕСОЗ sync + вкладка "Направлення" в картці пацієнта | ✅ Done |
| **Модуль 4** | Е-рецепт + перевірка алергій (HTTP 409) + Mock ЕСОЗ синхронізація | ✅ Done |
| **Модуль 5** | Онлайн-запис + Redis lock + Celery нагадування | ✅ Done |
| **Модуль 6** | Кабінет пацієнта (профіль, аватар, ЕМК ro, записи) | ✅ Done |
| **Модуль 7** | Адмін-панель (юзери, audit log) + Аналітика (5 метрик) | ✅ Done |
| **Email** | OTP + скидання пароля + нагадування (fastapi-mail; консоль + SMTP) | ✅ Done |
| **Frontend** | React SPA — 21 сторінка + вкладка Направлення (лікар, пацієнт, адмін, auth) | ✅ Done |
| **Dockerfiles** | `backend/Dockerfile`, `esoz-mock/Dockerfile`, `frontend/Dockerfile` (multi-stage nginx) | ✅ Done |
| **docker-compose.yml** | Повний стек одною командою: інфраструктура + backend + esoz-mock + frontend | ✅ Done |
| **Тести** | 93 тести: AuthService, PatientService, Auth API, Patient Cabinet API | ✅ Done |

### Що ще не реалізовано
| Компонент | Пріоритет | Деталі |
|-----------|-----------|--------|
| **Тести (решта)** | Важливо | Потрібні: encounters, prescriptions, appointments, analytics, admin API |

---

## Перевірка алергій при рецепті

При виписуванні рецепту система автоматично перевіряє алергії пацієнта.
Якщо INN препарату збігається з речовиною алергії — повертається `HTTP 409`:

```json
{
  "warning": "Drug INN matches patient allergy",
  "allergy": "Пеніцилін",
  "drug_inn": "амоксицилін пеніцилін",
  "severity": "HIGH"
}
```

Лікар може проігнорувати попередження, натиснувши підтвердження у фронтенді.
У консолі виводиться: `[ALLERGY] Drug '...' conflicts with patient allergy '...'`

---

## Email-сервіс

Реалізовано через `fastapi-mail`. Всі функції **завжди виводять дані в консоль** (для dev-спостереження) і додатково надсилають реальний email, якщо налаштовано SMTP.

**Що надсилається:**
- OTP-код при вході → `[DEV] OTP email → user@example.com | code: 482931`
- Посилання для скидання пароля → `[DEV] Password reset email → user@example.com | token: ...`
- Нагадування про запис (24h/1h) → `[DEV] Reminder email (24h) → user@example.com | ...`

**Увімкнути реальне надсилання** — додати в `backend/.env`:
```env
SMTP_HOST=smtp.mailtrap.io    # або smtp.gmail.com
SMTP_PORT=2525                # Mailtrap; для Gmail — 587
SMTP_USER=your_username
SMTP_PASSWORD=your_password
```
Якщо `SMTP_USER` або `SMTP_PASSWORD` порожні — email пропускається беззвучно, консоль завжди працює.

---

## Frontend — реалізовані сторінки

**Стек:** React 18 + TypeScript + Vite + React Router v6 + Zustand + Axios + Tailwind CSS + Recharts + react-qr-code

**DOCTOR** (`/doctor/*`):
- `/doctor` — Дашборд: прийоми на сьогодні
- `/doctor/patients` — Пошук пацієнтів
- `/doctor/patients/:id` — Карта пацієнта (вкладки: ЕМК, Прийоми, Рецепти, **Направлення**, Документи)
- `/doctor/encounters/new` — Новий прийом (автозбереження 30с, ICD-10, рецепт)
- `/doctor/patients/new` — Реєстрація нового пацієнта

**PATIENT** (`/patient/*`):
- `/patient` — Дашборд: наступний запис, активні рецепти, останній прийом
- `/patient/profile` — Профіль + аватар + зміна пароля
- `/patient/medical-card` — ЕМК тільки для читання
- `/patient/encounters` — Мої прийоми + PDF завантаження
- `/patient/prescriptions` — Рецепти з QR-кодом (esoz_request_number)
- `/patient/appointments` — Мої записи + запис до лікаря
- `/patient/book-appointment` — Вибір лікаря → дата → слот → бронювання
- `/patient/documents` — Мої документи

**ADMIN** (`/admin/*`):
- `/admin` — Дашборд: статистика + 4 Recharts графіки (аналітика)
- `/admin/users` — Таблиця користувачів (фільтри, пагінація)
- `/admin/users/:id` — Деталі юзера + деактивація + зміна ролі
- `/admin/audit-logs` — Журнал дій (фільтри: юзер, дія, дата)

**Auth** (публічні):
- `/login` → `/login/2fa` → (redirect by role)
- `/forgot-password` → `/reset-password?token=...`

---

## Тести

**Вимога:** Docker Desktop запущений (`docker compose up -d`).
Тести використовують окрему базу даних `medlink_test` (створюється автоматично).

> **Статус: 93/93 тестів проходять** (перевірено на Windows, Python 3.11)

```
backend/tests/
├── conftest.py                      # FakeRedis, NullPool test engine (medlink_test), clean_db, user fixtures
├── unit/
│   ├── test_auth_service.py         # 25 тестів: register, login, OTP, lockout, tokens, password reset
│   └── test_patient_service.py      # 22 тести: CRUD, пошук, access control, алергії, медкарта
└── integration/
    ├── test_auth_api.py             # 25 тестів: повний 2FA flow, refresh, logout, /me, reset password
    └── test_patient_cabinet_api.py  # 21 тест: GET/PATCH /me, медкарта, прийоми, рецепти, change-password
```

Разом: **93 тести** (47 unit + 46 integration).

**Конфігурація (`pytest.ini`):** `asyncio_mode = auto`, `asyncio_default_fixture_loop_scope = session`

**Windows-специфічні виправлення в `conftest.py`:**
- `asyncio.WindowsSelectorEventLoopPolicy()` — замість ProactorEventLoop для сумісності з asyncpg
- `poolclass=NullPool` на test_engine — нові з'єднання для кожного тесту, без пулу
- `db_session` закриває сесію в `try/except` щоб придушити помилки teardown

```bash
cd backend
pytest -v                              # всі 93 тести
pytest tests/unit/ -v                  # тільки unit (швидко)
pytest --cov=app --cov-report=html -v  # з покриттям → htmlcov/index.html
```

---

## 🔑 Тест авторизації (curl)
```bash
# Реєстрація
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"doctor@test.com","password":"Test1234!","first_name":"Іван","last_name":"Лікаренко","role":"DOCTOR"}'

# Логін (OTP виводиться в консолі uvicorn і надсилається на email якщо SMTP налаштовано)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"doctor@test.com","password":"Test1234!"}'

# 2FA (замінити OTP з консолі)
curl -X POST http://localhost:8000/api/v1/auth/login/2fa \
  -H "Content-Type: application/json" \
  -d '{"email":"doctor@test.com","otp_code":"482931"}'

# Скидання пароля (токен виводиться в консолі і надсилається на email)
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
# Виписати рецепт (автоматична перевірка алергій — HTTP 409 якщо конфлікт)
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
