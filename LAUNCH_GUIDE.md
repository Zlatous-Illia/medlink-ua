# Інструкція по запуску MedLink UA

## Передумови

- **Docker Desktop** — встановлено і запущено
- **Python 3.11+** — встановлено
- **Node.js 20+** — встановлено

---

## Крок 1 — Запустити інфраструктуру (PostgreSQL, Redis, MinIO)

```bash
# В кореневій директорії проекту
cd C:\Users\Admin\Desktop\Student\Diploma\medlink-ua
docker compose up -d
```

Перевірити статус:
```bash
docker compose ps
```
Всі три сервіси (postgres, redis, minio) повинні мати статус `healthy`.

---

## Крок 2 — Налаштувати та запустити Backend

**Термінал 1:**
```bash
cd backend

# Активувати venv (якщо є)
# venv\Scripts\activate

pip install -r requirements.txt

# Налаштувати .env (якщо ще не зроблено)
cp .env.example .env
# Відредагуйте .env якщо потрібно — мінімум SECRET_KEY вже задано

# Застосувати міграції
alembic upgrade head

# Запустити API сервер
uvicorn app.main:app --reload --port 8000
```

Backend буде доступний на: http://localhost:8000
Swagger документація: http://localhost:8000/docs

---

## Крок 3 — Запустити Mock ЕСОЗ

**Термінал 2:**
```bash
cd esoz-mock
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

Mock ЕСОЗ Swagger: http://localhost:8080/docs

---

## Крок 4 — Запустити Frontend

**Термінал 3:**
```bash
cd frontend
npm install        # (вже виконано раніше, але на всяк випадок)
npm run dev
```

Frontend буде доступний на: http://localhost:5173

---

## Крок 5 — (Опціонально) Celery Worker для email-нагадувань

**Термінал 4:**
```bash
cd backend
celery -A app.workers.celery_app worker --loglevel=info
```

---

## Зведена таблиця сервісів

| Сервіс | URL | Опис |
|--------|-----|------|
| Frontend | http://localhost:5173 | React SPA (основний інтерфейс) |
| Backend API | http://localhost:8000 | FastAPI сервер |
| Backend Swagger | http://localhost:8000/docs | Інтерактивна документація API |
| Mock ЕСОЗ | http://localhost:8080 | Симуляція НСЗУ API |
| Mock ЕСОЗ Swagger | http://localhost:8080/docs | Документація Mock ЕСОЗ |
| MinIO Console | http://localhost:9001 | Файлове сховище (admin/minioadmin123) |

---

## Швидкий старт — тестові акаунти

### Крок 1: Реєстрація через Swagger або curl

```bash
# Зареєструвати лікаря
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "doctor@test.com",
    "password": "Test1234!",
    "first_name": "Іван",
    "last_name": "Лікаренко",
    "role": "DOCTOR"
  }'

# Зареєструвати пацієнта
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "patient@test.com",
    "password": "Patient1234!",
    "first_name": "Олена",
    "last_name": "Коваленко",
    "role": "PATIENT"
  }'

# Зареєструвати адміна
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@test.com",
    "password": "Admin1234!",
    "first_name": "Марія",
    "last_name": "Адміненко",
    "role": "ADMIN"
  }'
```

### Крок 2: Вхід через Frontend

1. Відкрийте http://localhost:5173
2. Введіть email і пароль → натисніть "Увійти"
3. **Важливо:** OTP-код виводиться в термінал Backend (Термінал 1), шукайте рядок:
   ```
   DEV OTP for doctor@test.com: 123456
   ```
4. Введіть 6-значний код на сторінці 2FA

### Авто-редирект після входу:
- **DOCTOR** → `/doctor` (Дашборд лікаря з прийомами на сьогодні)
- **PATIENT** → `/patient` (Дашборд пацієнта)
- **ADMIN/SUPER_ADMIN** → `/admin` (Адмін-панель з аналітикою)

---

## Імпорт довідників (для повноцінного тестування)

```bash
cd backend

# Імпорт МКБ-10 (потрібен файл icd10.csv)
# CSV формат: code,name_ua,name_en,category
python scripts/import_icd10.py icd10.csv

# Імпорт препаратів (потрібен файл drugs.csv)
# CSV формат: atc_code,inn,trade_name,form,dosage,manufacturer
python scripts/import_drugs.py drugs.csv
```

Без довідників:
- ICD-10 пошук повертатиме порожній список
- Пошук препаратів повертатиме порожній список

---

## Що реалізовано у Frontend

### Авторизація (`/login`, `/login/2fa`)
- Вхід email+пароль → редирект на 2FA
- 6-значний OTP (з консолі сервера)
- Скидання пароля (`/forgot-password`, `/reset-password`)
- Auto-refresh JWT токена (прозоро для користувача)

### Робоче місце лікаря (`/doctor/*`)
- Дашборд з прийомами на сьогодні
- Пошук і реєстрація пацієнтів
- Карта пацієнта (ЕМК, прийоми, рецепти, документи)
- Новий прийом: скарги, анамнез, об'єктивний огляд, план лікування
- Автозбереження кожні 30 секунд
- Пошук і додавання МКБ-10 діагнозів
- Виписка е-рецепту з пошуком препаратів
- Попередження про алергію при виборі препарату
- Завершення прийому

### Кабінет пацієнта (`/patient/*`)
- Дашборд з активними рецептами і записами
- Профіль: редагування ПІБ, телефону, завантаження аватара
- Зміна пароля
- Медкартка (тільки читання): алергії, хронічні хвороби
- Мої прийоми з посиланнями на PDF виписки
- Рецепти: активні/всі, QR-код (esoz_request_number)
- Записи до лікаря: скасування, нові записи
- Запис до лікаря: вибір лікаря → дата → вільний слот → підтвердження
- Мої документи: перегляд і завантаження

### Адмін-панель (`/admin/*`)
- Дашборд: статистика + 4 графіки (Recharts)
  - Записи по місяцях (LineChart)
  - Топ-10 діагнозів (BarChart)
  - Навантаження лікарів (BarChart)
  - Відсоток скасувань
- Список користувачів з фільтрами (роль, статус, пошук)
- Деталі користувача + деактивація + зміна ролі (SUPER_ADMIN)
- Журнал дій (audit log) з фільтрами

---

## Відомі обмеження

1. **OTP на email не відправляється** — код виводиться тільки в консоль uvicorn (DEV режим)
2. **Нагадування про прийоми** — тільки print() у Celery, реальний email не налаштовано
3. **ICD-10 і Drugs** — потрібен імпорт CSV-файлів, інакше пошук порожній
4. **MinIO для аватарів/документів** — файли зберігаються, але URL може бути недоступний ззовні без додаткового налаштування

---

## Зупинка всіх сервісів

```bash
# Зупинити Docker контейнери
docker compose down

# Зупинити Python/Node процеси — Ctrl+C у відповідних терміналах
```
