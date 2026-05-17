import { createBrowserRouter, Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import type { UserRole } from '../api/types'

// ── Lazy imports ──────────────────────────────────────────────────────────────
import { LoginPage } from '../pages/auth/LoginPage'
import { TwoFAPage } from '../pages/auth/TwoFAPage'
import { ForgotPasswordPage } from '../pages/auth/ForgotPasswordPage'
import { ResetPasswordPage } from '../pages/auth/ResetPasswordPage'
import { RegisterPage } from '../pages/auth/RegisterPage'

import { DoctorDashboard } from '../pages/doctor/DoctorDashboard'
import { PatientSearchPage } from '../pages/doctor/PatientSearchPage'
import { PatientDetailPage } from '../pages/doctor/PatientDetailPage'
import { NewEncounterPage } from '../pages/doctor/NewEncounterPage'
import { RegisterPatientPage } from '../pages/doctor/RegisterPatientPage'

import { PatientDashboard } from '../pages/patient/PatientDashboard'
import { MyProfilePage } from '../pages/patient/MyProfilePage'
import { MyMedicalCardPage } from '../pages/patient/MyMedicalCardPage'
import { MyEncountersPage } from '../pages/patient/MyEncountersPage'
import { MyReferralsPage } from '../pages/patient/MyReferralsPage'
import { MyPrescriptionsPage } from '../pages/patient/MyPrescriptionsPage'
import { MyAppointmentsPage } from '../pages/patient/MyAppointmentsPage'
import { BookAppointmentPage } from '../pages/patient/BookAppointmentPage'
import { MyDocumentsPage } from '../pages/patient/MyDocumentsPage'

import { AdminDashboard } from '../pages/admin/AdminDashboard'
import { UsersListPage } from '../pages/admin/UsersListPage'
import { UserDetailPage } from '../pages/admin/UserDetailPage'
import { AuditLogPage } from '../pages/admin/AuditLogPage'
import { AdminPatientsPage } from '../pages/admin/AdminPatientsPage'

import { AppShell } from '../components/layout/AppShell'

// ── Guards ────────────────────────────────────────────────────────────────────

function PrivateRoute({ roles }: { roles: UserRole[] }) {
  const { isAuthenticated, user } = useAuthStore()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (user && !roles.includes(user.role)) return <Navigate to="/" replace />
  return <Outlet />
}

function RoleRedirect() {
  const { isAuthenticated, user } = useAuthStore()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (!user) return <Navigate to="/login" replace />
  if (user.role === 'DOCTOR') return <Navigate to="/doctor" replace />
  if (user.role === 'PATIENT') return <Navigate to="/patient" replace />
  return <Navigate to="/admin" replace />
}

function WithShell({ children }: { children: React.ReactNode }) {
  return <AppShell>{children}</AppShell>
}

// ── Router ────────────────────────────────────────────────────────────────────

export const router = createBrowserRouter([
  { path: '/', element: <RoleRedirect /> },
  { path: '/login', element: <LoginPage /> },
  { path: '/register', element: <RegisterPage /> },
  { path: '/login/2fa', element: <TwoFAPage /> },
  { path: '/forgot-password', element: <ForgotPasswordPage /> },
  { path: '/reset-password', element: <ResetPasswordPage /> },

  // ── Doctor ─────────────────────────────────────────────────────────────────
  {
    element: <PrivateRoute roles={['DOCTOR']} />,
    children: [
      { path: '/doctor', element: <WithShell><DoctorDashboard /></WithShell> },
      { path: '/doctor/patients', element: <WithShell><PatientSearchPage /></WithShell> },
      { path: '/doctor/patients/new', element: <WithShell><RegisterPatientPage /></WithShell> },
      { path: '/doctor/patients/:id', element: <WithShell><PatientDetailPage /></WithShell> },
      { path: '/doctor/encounters/new', element: <WithShell><NewEncounterPage /></WithShell> },
    ],
  },

  // ── Patient ────────────────────────────────────────────────────────────────
  {
    element: <PrivateRoute roles={['PATIENT']} />,
    children: [
      { path: '/patient', element: <WithShell><PatientDashboard /></WithShell> },
      { path: '/patient/profile', element: <WithShell><MyProfilePage /></WithShell> },
      { path: '/patient/medical-card', element: <WithShell><MyMedicalCardPage /></WithShell> },
      { path: '/patient/encounters', element: <WithShell><MyEncountersPage /></WithShell> },
      { path: '/patient/referrals', element: <WithShell><MyReferralsPage /></WithShell> },
      { path: '/patient/prescriptions', element: <WithShell><MyPrescriptionsPage /></WithShell> },
      { path: '/patient/appointments', element: <WithShell><MyAppointmentsPage /></WithShell> },
      { path: '/patient/appointments/book', element: <WithShell><BookAppointmentPage /></WithShell> },
      { path: '/patient/documents', element: <WithShell><MyDocumentsPage /></WithShell> },
    ],
  },

  // ── Admin ──────────────────────────────────────────────────────────────────
  {
    element: <PrivateRoute roles={['ADMIN', 'SUPER_ADMIN']} />,
    children: [
      { path: '/admin', element: <WithShell><AdminDashboard /></WithShell> },
      { path: '/admin/users', element: <WithShell><UsersListPage /></WithShell> },
      { path: '/admin/users/:id', element: <WithShell><UserDetailPage /></WithShell> },
      { path: '/admin/patients', element: <WithShell><AdminPatientsPage /></WithShell> },
      { path: '/admin/patients/:id', element: <WithShell><PatientDetailPage /></WithShell> },
      { path: '/admin/encounters/new', element: <WithShell><NewEncounterPage /></WithShell> },
      { path: '/admin/audit-logs', element: <WithShell><AuditLogPage /></WithShell> },
    ],
  },
])
