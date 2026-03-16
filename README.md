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
│   │   ├── api/v1/   # REST роутери
│   │   ├── core/     # config, db, security, dependencies
│   │   ├── models/   # SQLAlchemy ORM
│   │   ├── schemas/  # Pydantic v2
│   │   └── services/ # бізнес-логіка + ЕСОЗ connector
│   └── alembic/      # міграції
├── esoz-mock/        # Mock ЕСОЗ API (порт 8080)
├── frontend/         # React 18 + TypeScript (порт 3000)
└── docker-compose.yml
```

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
```

## 📋 Модулі (план по тижнях)
- **Тиждень 1:** Авторизація + JWT + 2FA ✅
- **Тиждень 2:** Пацієнти + ЕМК
- **Тиждень 3:** Прийом лікаря + МКБ-10
- **Тиждень 4:** Е-рецепт + Mock ЕСОЗ
- **Тиждень 5:** Онлайн-запис
- **Тиждень 6:** Кабінет пацієнта
- **Тиждень 7:** Адмін-панель + Аналітика
- **Тиждень 8:** Тести + Документація
