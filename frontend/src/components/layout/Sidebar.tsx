import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Users, FileText, Pill, Calendar, Stethoscope,
  UserCircle, ClipboardList, ScrollText, FolderOpen, Heart,
} from 'lucide-react'
import type { UserRole } from '../../api/types'

const DOCTOR_NAV = [
  { to: '/doctor', icon: LayoutDashboard, label: 'Дашборд', end: true },
  { to: '/doctor/patients', icon: Users, label: 'Пацієнти' },
]

const PATIENT_NAV = [
  { to: '/patient', icon: LayoutDashboard, label: 'Дашборд', end: true },
  { to: '/patient/profile', icon: UserCircle, label: 'Мій профіль' },
  { to: '/patient/medical-card', icon: Heart, label: 'Медкартка' },
  { to: '/patient/encounters', icon: Stethoscope, label: 'Мої прийоми' },
  { to: '/patient/referrals', icon: FileText, label: 'Мої направлення' },
  { to: '/patient/prescriptions', icon: Pill, label: 'Рецепти' },
  { to: '/patient/appointments', icon: Calendar, label: 'Мої записи' },
  { to: '/patient/documents', icon: FolderOpen, label: 'Документи' },
]

const ADMIN_NAV = [
  { to: '/admin', icon: LayoutDashboard, label: 'Дашборд', end: true },
  { to: '/admin/users', icon: Users, label: 'Користувачі' },
  { to: '/admin/patients', icon: ClipboardList, label: 'Пацієнти' },
  { to: '/admin/audit-logs', icon: ScrollText, label: 'Журнал дій' },
]

interface Props {
  role: UserRole
}

export function Sidebar({ role }: Props) {
  const nav = role === 'DOCTOR' ? DOCTOR_NAV
    : role === 'PATIENT' ? PATIENT_NAV
    : ADMIN_NAV

  return (
    <nav className="flex flex-col gap-1 p-3">
      {nav.map(item => (
        <NavLink
          key={item.to}
          to={item.to}
          end={'end' in item ? item.end : false}
          className={({ isActive }) =>
            `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors
            ${isActive
              ? 'bg-blue-50 text-blue-700'
              : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'}`
          }
        >
          <item.icon className="h-4 w-4 shrink-0" />
          {item.label}
        </NavLink>
      ))}
    </nav>
  )
}
