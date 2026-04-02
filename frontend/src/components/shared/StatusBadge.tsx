import type { AppointmentStatus, PrescriptionStatus, EncounterStatus, UserRole } from '../../api/types'

type StatusValue = AppointmentStatus | PrescriptionStatus | EncounterStatus | UserRole | string

const COLORS: Record<string, string> = {
  // Appointment
  SCHEDULED: 'bg-blue-100 text-blue-700',
  CONFIRMED: 'bg-green-100 text-green-700',
  COMPLETED: 'bg-gray-100 text-gray-700',
  CANCELLED: 'bg-red-100 text-red-700',
  NO_SHOW: 'bg-orange-100 text-orange-700',
  // Prescription
  ACTIVE: 'bg-green-100 text-green-700',
  // Encounter
  IN_PROGRESS: 'bg-yellow-100 text-yellow-700',
  // Roles
  DOCTOR: 'bg-blue-100 text-blue-700',
  PATIENT: 'bg-teal-100 text-teal-700',
  ADMIN: 'bg-purple-100 text-purple-700',
  SUPER_ADMIN: 'bg-red-100 text-red-700',
}

const LABELS: Record<string, string> = {
  SCHEDULED: 'Заплановано',
  CONFIRMED: 'Підтверджено',
  COMPLETED: 'Завершено',
  CANCELLED: 'Скасовано',
  NO_SHOW: 'Не з\'явився',
  ACTIVE: 'Активний',
  IN_PROGRESS: 'В процесі',
  DOCTOR: 'Лікар',
  PATIENT: 'Пацієнт',
  ADMIN: 'Адмін',
  SUPER_ADMIN: 'Супер-адмін',
}

export function StatusBadge({ value }: { value: StatusValue }) {
  const color = COLORS[value] ?? 'bg-gray-100 text-gray-600'
  const label = LABELS[value] ?? value
  return (
    <span className={`badge ${color}`}>{label}</span>
  )
}
