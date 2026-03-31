# Промпт для реалізації Frontend — MedLink UA

## Контекст проекту

Ти реалізуєш **frontend** для MedLink UA — електронної медичної інформаційної системи (ЕМІС) для первинної ланки охорони здоров'я. Це дипломний проект.

**Backend вже повністю реалізований** — FastAPI + PostgreSQL + Redis + MinIO, порт 8000.
**Твоє завдання** — реалізувати SPA на React 18 + TypeScript, який покриває всі ролі: DOCTOR, PATIENT, ADMIN.

---

## Стек технологій

| Призначення | Технологія |
|---|---|
| Фреймворк | React 18 + TypeScript (Vite) |
| Роутинг | React Router v6 |
| Стейт | Zustand |
| Запити | axios + @tanstack/react-query v5 |
| Форми | React Hook Form + Zod |
| Стилі | Tailwind CSS + shadcn/ui |
| Графіки | Recharts |
| QR-код | react-qr-code |
| Іконки | lucide-react |

---

## Ініціалізація проекту

```bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install react-router-dom zustand axios @tanstack/react-query
npm install react-hook-form zod @hookform/resolvers
npm install recharts react-qr-code lucide-react
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
# Встановлення shadcn/ui (після налаштування tailwind)
npx shadcn-ui@latest init
npx shadcn-ui@latest add button input card badge table dialog select tabs avatar
```

**`vite.config.ts`** — додати proxy для API:
```ts
server: {
  proxy: {
    '/api': 'http://localhost:8000'
  }
}
```

---

## Структура директорій

```
frontend/src/
├── api/
│   ├── client.ts           # axios instance + interceptors (auth, refresh, retry)
│   ├── auth.ts             # функції для auth endpoints
│   ├── patients.ts         # функції для patients endpoints
│   ├── encounters.ts       # функції для encounters endpoints
│   ├── prescriptions.ts    # функції для prescriptions endpoints
│   ├── appointments.ts     # функції для appointments + doctors endpoints
│   ├── patientCabinet.ts   # функції для /me endpoints
│   ├── admin.ts            # функції для admin endpoints
│   ├── analytics.ts        # функції для analytics endpoints
│   └── types.ts            # TypeScript-типи (відповідають Pydantic-схемам бекенду)
├── store/
│   ├── authStore.ts        # Zustand: user, tokens, isAuthenticated, login/logout
│   └── uiStore.ts          # loading, toasts
├── router/
│   └── index.tsx           # всі маршрути з PrivateRoute
├── components/
│   ├── layout/
│   │   ├── AppShell.tsx    # sidebar + topbar wrapper
│   │   ├── Sidebar.tsx     # role-based navigation menu
│   │   └── Topbar.tsx      # user avatar, logout button
│   ├── shared/
│   │   ├── DataTable.tsx           # generic paginated table
│   │   ├── DateRangePicker.tsx     # picker для аналітики
│   │   ├── QRCodeCard.tsx          # картка з QR-кодом рецепту
│   │   ├── StatusBadge.tsx         # кольоровий badge статусу (ACTIVE, CANCELLED, etc.)
│   │   └── ConfirmDialog.tsx       # модалка підтвердження дії
│   └── forms/
│       ├── PatientForm.tsx         # форма реєстрації/редагування пацієнта
│       ├── EncounterForm.tsx       # форма прийому з автозбереженням
│       ├── PrescriptionForm.tsx    # форма рецепту з пошуком препаратів
│       └── AllergyWarningModal.tsx # попередження про алергію
├── pages/
│   ├── auth/
│   │   ├── LoginPage.tsx
│   │   ├── TwoFAPage.tsx
│   │   ├── ForgotPasswordPage.tsx
│   │   └── ResetPasswordPage.tsx
│   ├── doctor/
│   │   ├── DoctorDashboard.tsx
│   │   ├── PatientSearchPage.tsx
│   │   ├── PatientDetailPage.tsx
│   │   ├── NewEncounterPage.tsx
│   │   └── RegisterPatientPage.tsx
│   ├── patient/
│   │   ├── PatientDashboard.tsx
│   │   ├── MyProfilePage.tsx
│   │   ├── MyMedicalCardPage.tsx
│   │   ├── MyEncountersPage.tsx
│   │   ├── MyPrescriptionsPage.tsx
│   │   ├── MyAppointmentsPage.tsx
│   │   ├── BookAppointmentPage.tsx
│   │   └── MyDocumentsPage.tsx
│   └── admin/
│       ├── AdminDashboard.tsx
│       ├── UsersListPage.tsx
│       ├── UserDetailPage.tsx
│       └── AuditLogPage.tsx
└── main.tsx
```

---

## API Client (`src/api/client.ts`)

```typescript
import axios from 'axios'
import { useAuthStore } from '../store/authStore'

const client = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' }
})

// Attach token
client.interceptors.request.use(config => {
  const token = useAuthStore.getState().accessToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Refresh on 401
let isRefreshing = false
let queue: Array<(token: string) => void> = []

client.interceptors.response.use(
  res => res,
  async err => {
    const original = err.config
    if (err.response?.status === 401 && !original._retry) {
      original._retry = true
      if (!isRefreshing) {
        isRefreshing = true
        try {
          const refreshToken = useAuthStore.getState().refreshToken
          const { data } = await axios.post('/api/v1/auth/refresh', { refresh_token: refreshToken })
          useAuthStore.getState().setTokens(data.access_token, data.refresh_token)
          queue.forEach(cb => cb(data.access_token))
          queue = []
        } finally {
          isRefreshing = false
        }
      }
      return new Promise(resolve => {
        queue.push(token => {
          original.headers.Authorization = `Bearer ${token}`
          resolve(client(original))
        })
      })
    }
    return Promise.reject(err)
  }
)

export default client
```

---

## Auth Store (`src/store/authStore.ts`)

```typescript
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
  id: string
  email: string
  first_name: string
  last_name: string
  role: 'PATIENT' | 'DOCTOR' | 'ADMIN' | 'SUPER_ADMIN'
  avatar_url?: string
}

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  setUser: (user: User) => void
  setTokens: (access: string, refresh: string) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    set => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      setUser: user => set({ user }),
      setTokens: (accessToken, refreshToken) =>
        set({ accessToken, refreshToken, isAuthenticated: true }),
      logout: () =>
        set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false })
    }),
    { name: 'medlink-auth' }
  )
)
```

---

## TypeScript Types (`src/api/types.ts`)

Визнач інтерфейси відповідно до Pydantic-схем бекенду:

```typescript
export type Role = 'PATIENT' | 'DOCTOR' | 'ADMIN' | 'SUPER_ADMIN'
export type Gender = 'MALE' | 'FEMALE' | 'OTHER'
export type AppointmentStatus = 'SCHEDULED' | 'CONFIRMED' | 'COMPLETED' | 'CANCELLED' | 'NO_SHOW'
export type EncounterStatus = 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED'
export type PrescriptionStatus = 'ACTIVE' | 'COMPLETED' | 'CANCELLED'
export type BloodType = 'A+' | 'A-' | 'B+' | 'B-' | 'AB+' | 'AB-' | 'O+' | 'O-' | 'UNKNOWN'

export interface User {
  id: string
  email: string
  first_name: string
  last_name: string
  middle_name?: string
  role: Role
  phone?: string
  avatar_url?: string
  is_active: boolean
  created_at: string
}

export interface Patient {
  id: string
  tax_id: string
  first_name: string
  last_name: string
  middle_name?: string
  birth_date: string
  gender: Gender
  phone?: string
  email?: string
  address?: { street?: string; city?: string; region?: string; zip?: string }
  primary_doctor_id?: string
  esoz_person_id?: string
  is_active: boolean
  created_at: string
}

export interface MedicalCard {
  id: string
  patient_id: string
  blood_type?: BloodType
  height_cm?: number
  weight_kg?: number
  smoking_status?: 'NEVER' | 'FORMER' | 'CURRENT' | 'UNKNOWN'
  notes?: string
  allergies: Allergy[]
  chronic_diseases: ChronicDisease[]
  updated_at: string
}

export interface Allergy {
  id: string
  substance: string
  severity: 'MILD' | 'MODERATE' | 'SEVERE'
  reaction?: string
}

export interface ChronicDisease {
  id: string
  icd10_id: string
  icd10_code?: string
  icd10_name?: string
  diagnosed_at?: string
  notes?: string
}

export interface ICD10Code {
  id: string
  code: string
  name_ua: string
  name_en: string
}

export interface Drug {
  id: string
  atc_code?: string
  inn: string
  trade_name?: string
  form?: string
  dosage?: string
}

export interface Encounter {
  id: string
  patient_id: string
  doctor_id: string
  appointment_id?: string
  status: EncounterStatus
  started_at: string
  completed_at?: string
  complaints?: string
  anamnesis?: string
  objective_exam?: string
  treatment_plan?: string
  recommendations?: string
  pdf_url?: string
  diagnoses?: Diagnosis[]
}

export interface Diagnosis {
  id: string
  encounter_id: string
  icd10_id: string
  icd10_code?: string
  icd10_name?: string
  type: 'MAIN' | 'COMPLICATION' | 'CONCOMITANT'
  notes?: string
}

export interface Prescription {
  id: string
  encounter_id: string
  patient_id: string
  doctor_id: string
  drug_id: string
  drug?: Drug
  dosage: string
  frequency: string
  duration_days?: number
  quantity?: number
  instructions?: string
  status: PrescriptionStatus
  esoz_request_id?: string
  esoz_request_number?: string
  created_at: string
  expires_at?: string
}

export interface Doctor {
  id: string
  user_id: string
  full_name: string
  specialization?: string
  specialization_id?: string
  license_number?: string
  experience_years?: number
  bio?: string
  photo_url?: string
}

export interface TimeSlot {
  datetime: string
  is_available: boolean
}

export interface Appointment {
  id: string
  patient_id: string
  doctor_id: string
  doctor?: Doctor
  patient?: Patient
  slot_datetime: string
  duration_min: number
  reason?: string
  status: AppointmentStatus
  cancel_reason?: string
  created_at: string
}

export interface AuditLog {
  id: string
  user_id?: string
  user_email?: string
  action: string
  resource?: string
  resource_id?: string
  ip_address?: string
  details?: Record<string, unknown>
  created_at: string
}

export interface SystemStats {
  users_by_role: Record<Role, number>
  total_patients: number
  total_encounters: number
  total_prescriptions: number
  total_appointments: number
}

export interface AnalyticsPoint {
  period: string
  count: number
}

export interface DiagnosisTop {
  icd10_code: string
  icd10_name: string
  count: number
}

export interface DoctorLoad {
  doctor_id: string
  doctor_name: string
  encounters_count: number
  appointments_count: number
}
```

---

## Роутер (`src/router/index.tsx`)

```tsx
import { createBrowserRouter, Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

function PrivateRoute({ roles }: { roles: string[] }) {
  const { isAuthenticated, user } = useAuthStore()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (!roles.includes(user!.role)) return <Navigate to="/" replace />
  return <Outlet />
}

function RoleRedirect() {
  const { user } = useAuthStore()
  if (!user) return <Navigate to="/login" />
  if (user.role === 'DOCTOR') return <Navigate to="/doctor" />
  if (user.role === 'PATIENT') return <Navigate to="/patient" />
  return <Navigate to="/admin" />
}

export const router = createBrowserRouter([
  { path: '/', element: <RoleRedirect /> },
  { path: '/login', element: <LoginPage /> },
  { path: '/login/2fa', element: <TwoFAPage /> },
  { path: '/forgot-password', element: <ForgotPasswordPage /> },
  { path: '/reset-password', element: <ResetPasswordPage /> },

  {
    element: <PrivateRoute roles={['DOCTOR']} />,
    children: [
      { path: '/doctor', element: <AppShell><DoctorDashboard /></AppShell> },
      { path: '/doctor/patients', element: <AppShell><PatientSearchPage /></AppShell> },
      { path: '/doctor/patients/new', element: <AppShell><RegisterPatientPage /></AppShell> },
      { path: '/doctor/patients/:id', element: <AppShell><PatientDetailPage /></AppShell> },
      { path: '/doctor/encounters/new', element: <AppShell><NewEncounterPage /></AppShell> },
    ]
  },

  {
    element: <PrivateRoute roles={['PATIENT']} />,
    children: [
      { path: '/patient', element: <AppShell><PatientDashboard /></AppShell> },
      { path: '/patient/profile', element: <AppShell><MyProfilePage /></AppShell> },
      { path: '/patient/medical-card', element: <AppShell><MyMedicalCardPage /></AppShell> },
      { path: '/patient/encounters', element: <AppShell><MyEncountersPage /></AppShell> },
      { path: '/patient/prescriptions', element: <AppShell><MyPrescriptionsPage /></AppShell> },
      { path: '/patient/appointments', element: <AppShell><MyAppointmentsPage /></AppShell> },
      { path: '/patient/appointments/book', element: <AppShell><BookAppointmentPage /></AppShell> },
      { path: '/patient/documents', element: <AppShell><MyDocumentsPage /></AppShell> },
    ]
  },

  {
    element: <PrivateRoute roles={['ADMIN', 'SUPER_ADMIN']} />,
    children: [
      { path: '/admin', element: <AppShell><AdminDashboard /></AppShell> },
      { path: '/admin/users', element: <AppShell><UsersListPage /></AppShell> },
      { path: '/admin/users/:id', element: <AppShell><UserDetailPage /></AppShell> },
      { path: '/admin/audit-logs', element: <AppShell><AuditLogPage /></AppShell> },
    ]
  }
])
```

---

## Детальний опис сторінок

### Auth

**LoginPage** — форма: email, password (React Hook Form + Zod `email().min(8)`). На submit:
1. `POST /api/v1/auth/login` → отримати `{ message, user_id }`
2. Зберегти `user_id` в sessionStorage (для 2FA step)
3. Redirect → `/login/2fa`

**TwoFAPage** — 6 окремих `<input type="text" maxLength={1}>` для OTP, автофокус між полями. На submit:
1. `POST /api/v1/auth/login/2fa` → отримати `{ access_token, refresh_token, user }`
2. `authStore.setTokens()` + `authStore.setUser()`
3. Redirect → `/` (RoleRedirect спрямує за роллю)

**ForgotPasswordPage** — email форма → `POST /api/v1/auth/forgot-password`. Показати success banner "Токен виведено в консоль сервера (dev режим)".

**ResetPasswordPage** — зчитати `?token=` з URL. Форма: new_password + confirm. → `POST /api/v1/auth/reset-password`.

---

### Doctor workspace

**DoctorDashboard** — `useQuery(['appointments-today'], () => api.get('/appointments/today'))`. Список карток: час | пацієнт | причина | статус badge. Кнопка "Почати прийом" → `/doctor/encounters/new?appointment_id=...&patient_id=...`.

**PatientSearchPage** — `<input>` з debounce 300ms → `GET /api/v1/patients?search=...`. Таблиця: ПІБ, ІПН, дата народж., телефон. Клік → `/doctor/patients/:id`. Кнопка "Новий пацієнт" → `/doctor/patients/new`.

**PatientDetailPage** — завантажити `GET /api/v1/patients/:id`. Tabs (shadcn/ui):
- **ЕМК** — `GET /api/v1/patients/:id/medical-card`. Відображення: група крові, алергії (список з severity badge), хронічні хвороби з ICD-10 кодами. Кнопки "Додати алергію" і "Додати діагноз" відкривають Dialog-форми.
- **Прийоми** — `GET /api/v1/encounters/patients/:id/encounters`. Accordion з діагнозами. Кнопка "Скачати PDF".
- **Рецепти** — `GET /api/v1/prescriptions/patients/:id/prescriptions`. Таблиця зі статусами.
- **Документи** — з даних пацієнта. Upload форма `POST /api/v1/patients/:id/documents`.

**NewEncounterPage** — логіка:
1. На mount якщо є `?appointment_id=` і `?patient_id=` — `POST /api/v1/encounters { patient_id, appointment_id }` → отримати `encounter.id`
2. Форма textarea: скарги, анамнез, об'єктивний огляд, план лікування, рекомендації
3. Автозбереження: `useEffect` з `setInterval(30000)` → `PATCH /api/v1/encounters/:id`
4. ICD-10 combobox: `GET /api/v1/icd10/search?q=...` → вибрати → `POST /api/v1/encounters/:id/diagnoses`
5. Блок рецепту: drug search combobox → поля → перевірка алергій → `POST /api/v1/prescriptions`
6. Кнопка "Завершити прийом" → `POST /api/v1/encounters/:id/complete` → redirect to patient card

**AllergyWarningModal** — після вибору препарату в PrescriptionForm: якщо `drug.inn` входить до `patient.allergies[].substance` (case-insensitive) — показати Modal з попередженням і кнопками "Все одно виписати" / "Скасувати". Перевірку зроби на frontend side, бо бекенд поки не реалізував цю валідацію.

---

### Patient cabinet

**PatientDashboard** — 3 stat cards:
- Наступний запис: `GET /api/v1/me` → знайти найближчий appointment
- Активні рецепти: `GET /api/v1/me/prescriptions?status=ACTIVE` → `.length`
- Останній прийом: `GET /api/v1/me/encounters` → перший в списку

**MyProfilePage** — форма (React Hook Form): first_name, last_name, middle_name, phone (email не редагується). `PATCH /api/v1/me`. Секція аватару: preview `<img>` + `<input type="file" accept="image/jpeg,image/png">` + `POST /api/v1/me/avatar` (FormData). Секція паролю: current_password, new_password, confirm — `PATCH /api/v1/me/change-password`.

**MyMedicalCardPage** — read-only картка: `GET /api/v1/me/medical-card`. Група крові, зріст, вага. Таблиця алергій з severity badge. Таблиця хронічних хвороб з ICD-10.

**MyPrescriptionsPage** — Tabs: "Активні" / "Всі". `GET /api/v1/me/prescriptions?status=ACTIVE`. Картка рецепту: назва препарату, дозування, частота, термін. Якщо `esoz_request_number` є — показати `<QRCodeCard value={esoz_request_number} />`.

**BookAppointmentPage** — multi-step:
1. Список лікарів `GET /api/v1/doctors` з фільтром по спеціальності
2. Calendar picker → `GET /api/v1/doctors/:id/slots?date=YYYY-MM-DD`
3. Grid доступних слотів (кнопки з часом)
4. Форма причини звернення → `POST /api/v1/appointments`
5. Success → redirect `/patient/appointments`

---

### Admin panel

**AdminDashboard** — 5 stat cards (`GET /api/v1/admin/stats`): пацієнти, лікарі, прийоми, рецепти, записи. Нижче 4 графіки Recharts:
- `LineChart` — Прийоми по місяцях (`GET /api/v1/analytics/appointments?group_by=month`)
- `BarChart` — Топ-10 діагнозів (`GET /api/v1/analytics/diagnoses/top10`)
- `BarChart` — Навантаження лікарів (`GET /api/v1/analytics/doctors/load`)
- `LineChart` — Відсоток скасувань (`GET /api/v1/analytics/appointments/cancellation-rate`)

Для кожного графіка — `DateRangePicker` для фільтрації.

**UsersListPage** — `<DataTable>` з серверною пагінацією (`GET /api/v1/admin/users?page=1&limit=20&role=...`). Колонки: email, ім'я, роль badge, статус badge, дата реєстрації. Клік на рядок → `/admin/users/:id`. Фільтри: роль (Select), статус (is_active).

**UserDetailPage** — `GET /api/v1/admin/users/:id`. Картка: всі дані + кількість audit-подій. Кнопка деактивації (`POST /api/v1/admin/users/:id/deactivate`) з ConfirmDialog. Select для зміни ролі (тільки SUPER_ADMIN бачить цю опцію) → `PATCH /api/v1/admin/users/:id`.

**AuditLogPage** — `<DataTable>` з серверною пагінацією (`GET /api/v1/admin/audit-logs`). Фільтри: action (input), resource (input), DateRangePicker. Колонки: час, email юзера, дія, ресурс, IP.

---

## Layout — AppShell і Sidebar

**AppShell** — layout: `flex h-screen`. Зліва `<Sidebar>` (w-64), справа `<main className="flex-1 overflow-auto p-6">`.

**Sidebar** — nav-меню залежно від `user.role`:

| DOCTOR | PATIENT | ADMIN |
|---|---|---|
| Дашборд | Дашборд | Дашборд |
| Пацієнти | Мій профіль | Користувачі |
| - | Медкартка | Журнал дій |
| - | Прийоми | - |
| - | Рецепти | - |
| - | Записи | - |
| - | Документи | - |

Внизу sidebar — аватар + ім'я + кнопка logout (`POST /api/v1/auth/logout` → `authStore.logout()` → redirect `/login`).

---

## Загальні вимоги до якості UI

1. **Всі форми** — валідація через Zod, помилки відображаються під полями
2. **Loading states** — Skeleton або Spinner для всіх `useQuery`
3. **Error states** — toast або inline error message при API failures
4. **Empty states** — ілюстрація/текст "Немає даних" для порожніх таблиць
5. **Responsive** — мобільна версія через Tailwind `sm:` / `md:` breakpoints; sidebar collapse на малих екранах
6. **Dates** — відображати в форматі `dd.MM.yyyy HH:mm` (використати `date-fns/format` або `Intl.DateTimeFormat`)
7. **TypeScript** — без `any`. Всі API-відповіді типізовані через `types.ts`
8. **Token expiry** — після успішного refresh не показувати помилки юзеру, ретраї прозорі

---

## Важливі деталі бекенду

- `POST /auth/login` повертає `{ message: "OTP sent", user_id: "..." }` — НЕ токени! Токени приходять тільки після 2FA
- OTP в **DEV режимі** виводиться в консоль uvicorn (не на email), тому при тестуванні треба дивитись термінал бекенду
- `GET /api/v1/me/prescriptions` — PATIENT endpoint, `GET /api/v1/prescriptions/patients/:id/prescriptions` — DOCTOR endpoint
- `GET /api/v1/appointments/today` — повертає ТІЛЬКИ записи на поточний день поточного лікаря
- Слоти генеруються динамічно на основі `Schedule` шаблону — якщо лікар не має розкладу, слотів не буде
- `esoz_request_number` на рецепті з'являється тільки після успішного sync з Mock ЕСОЗ (може бути `null` якщо Mock ЕСОЗ недоступний)
- Аватар завантажується як `multipart/form-data` з полем `file`
- PDF отримується через `GET /api/v1/encounters/:id/pdf` — бекенд повертає redirect до MinIO URL або стрім

---

## Порядок реалізації (рекомендований)

1. **Ініціалізація проекту** — Vite, Tailwind, shadcn/ui, структура папок
2. **API client + types** — `client.ts`, `types.ts`, всі API-модулі
3. **Auth store + Login flow** — LoginPage → TwoFAPage → RoleRedirect
4. **AppShell + Sidebar** — layout з role-based nav
5. **Doctor: DoctorDashboard + PatientSearchPage** — перші функціональні сторінки
6. **Doctor: PatientDetailPage** — tabs з ЕМК
7. **Doctor: NewEncounterPage** — найскладніша сторінка (автозбереження, ICD-10, рецепт)
8. **Patient: PatientDashboard + MyProfilePage**
9. **Patient: MyPrescriptionsPage** — QR-коди
10. **Patient: BookAppointmentPage** — multi-step booking
11. **Admin: AdminDashboard** — charts
12. **Admin: UsersListPage + UserDetailPage + AuditLogPage**
13. **ForgotPassword + ResetPassword**
14. **Responsive polish** — мобільна версія

---

## Команди розробки

```bash
# Запустити frontend dev server
cd frontend
npm run dev           # http://localhost:5173

# Бекенд (окремий термінал)
cd backend
uvicorn app.main:app --reload --port 8000

# Mock ЕСОЗ (ще один термінал)
cd esoz-mock
uvicorn app.main:app --reload --port 8080

# Інфраструктура
docker compose up -d  # PostgreSQL, Redis, MinIO
```
