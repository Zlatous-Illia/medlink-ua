import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { format } from 'date-fns'
import { uk } from 'date-fns/locale'
import { Clock, User, Stethoscope, Plus } from 'lucide-react'
import { encountersApi } from '../../api/encounters'
import { useAuthStore } from '../../store/authStore'
import { StatusBadge } from '../../components/shared/StatusBadge'
import { PageLoading } from '../../components/shared/LoadingSpinner'
import { EmptyState } from '../../components/shared/EmptyState'

export function DoctorDashboard() {
  const user = useAuthStore(s => s.user)
  const navigate = useNavigate()

  const { data: appointments, isLoading } = useQuery({
    queryKey: ['today-appointments'],
    queryFn: () => encountersApi.todayAppointments().then(r => r.data),
  })

  const today = format(new Date(), 'EEEE, d MMMM yyyy', { locale: uk })

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">
          Вітаємо, {user?.first_name}!
        </h1>
        <p className="text-sm text-gray-500 mt-1 capitalize">{today}</p>
      </div>

      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">
          Прийоми на сьогодні
          {appointments && (
            <span className="ml-2 text-sm font-normal text-gray-500">
              ({appointments.length})
            </span>
          )}
        </h2>
        <button
          onClick={() => navigate('/doctor/encounters/new')}
          className="btn-primary btn-sm btn"
        >
          <Plus className="h-4 w-4" />
          Новий прийом
        </button>
      </div>

      {isLoading ? (
        <PageLoading />
      ) : !appointments?.length ? (
        <div className="card p-4">
          <EmptyState message="На сьогодні прийомів немає" />
        </div>
      ) : (
        <div className="grid gap-3">
          {appointments.map(appt => (
            <div key={appt.id} className="card p-4 flex items-center gap-4">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-blue-50">
                <User className="h-5 w-5 text-blue-600" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-900">
                  {appt.patient
                    ? `${appt.patient.last_name} ${appt.patient.first_name} ${appt.patient.middle_name ?? ''}`
                    : 'Пацієнт'}
                </p>
                {appt.reason && (
                  <p className="text-sm text-gray-500 truncate">{appt.reason}</p>
                )}
              </div>
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1 text-sm text-gray-600">
                  <Clock className="h-3.5 w-3.5" />
                  {format(new Date(appt.slot_datetime), 'HH:mm')}
                </div>
                <StatusBadge value={appt.status} />
              </div>
              {appt.patient && (
                <button
                  onClick={() => navigate(`/doctor/encounters/new?patient_id=${appt.patient?.id}&appointment_id=${appt.id}`)}
                  className="btn-secondary btn-sm btn shrink-0"
                >
                  <Stethoscope className="h-3.5 w-3.5" />
                  Почати
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
