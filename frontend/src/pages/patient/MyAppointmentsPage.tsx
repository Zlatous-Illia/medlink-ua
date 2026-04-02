import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { format } from 'date-fns'
import { Plus, X } from 'lucide-react'
import { appointmentsApi } from '../../api/appointments'
import { StatusBadge } from '../../components/shared/StatusBadge'
import { ConfirmDialog } from '../../components/shared/ConfirmDialog'
import { PageLoading } from '../../components/shared/LoadingSpinner'
import { EmptyState } from '../../components/shared/EmptyState'
import { toast } from '../../components/shared/Toast'
import { useState } from 'react'

export function MyAppointmentsPage() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [cancelId, setCancelId] = useState<string | null>(null)

  const { data: appointments, isLoading } = useQuery({
    queryKey: ['my-appointments'],
    queryFn: () => appointmentsApi.list({ limit: 50 }).then(r => r.data),
  })

  const cancelMutation = useMutation({
    mutationFn: (id: string) => appointmentsApi.cancel(id, 'Скасовано пацієнтом'),
    onSuccess: () => {
      toast('success', 'Запис скасовано')
      qc.invalidateQueries({ queryKey: ['my-appointments'] })
      setCancelId(null)
    },
    onError: () => toast('error', 'Помилка скасування'),
  })

  if (isLoading) return <PageLoading />

  const upcoming = appointments?.filter(a =>
    ['SCHEDULED', 'CONFIRMED'].includes(a.status)
  ) ?? []
  const past = appointments?.filter(a =>
    !['SCHEDULED', 'CONFIRMED'].includes(a.status)
  ) ?? []

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Мої записи</h1>
        <button onClick={() => navigate('/patient/appointments/book')} className="btn-primary btn">
          <Plus className="h-4 w-4" />
          Записатись
        </button>
      </div>

      {/* Upcoming */}
      <section className="mb-8">
        <h2 className="text-base font-semibold text-gray-700 mb-3">
          Майбутні записи ({upcoming.length})
        </h2>
        {!upcoming.length ? (
          <div className="card p-4"><EmptyState message="Майбутніх записів немає" /></div>
        ) : (
          <div className="space-y-3">
            {upcoming.map(appt => (
              <div key={appt.id} className="card p-4 flex items-center gap-4">
                <div className="flex-1">
                  <p className="font-medium text-gray-900">
                    {appt.doctor?.full_name ?? 'Лікар'}
                  </p>
                  {appt.doctor?.specialization && (
                    <p className="text-xs text-gray-500">{appt.doctor.specialization.name_ua}</p>
                  )}
                  <p className="text-sm text-gray-600 mt-1">
                    {format(new Date(appt.slot_datetime), 'dd.MM.yyyy, HH:mm')}
                  </p>
                  {appt.reason && <p className="text-xs text-gray-400 mt-1">{appt.reason}</p>}
                </div>
                <StatusBadge value={appt.status} />
                <button
                  onClick={() => setCancelId(appt.id)}
                  className="btn-secondary btn-sm btn text-red-600 hover:text-red-700"
                  title="Скасувати"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Past */}
      {past.length > 0 && (
        <section>
          <h2 className="text-base font-semibold text-gray-700 mb-3">
            Минулі записи ({past.length})
          </h2>
          <div className="space-y-2">
            {past.map(appt => (
              <div key={appt.id} className="card p-4 flex items-center gap-4 opacity-75">
                <div className="flex-1">
                  <p className="font-medium text-gray-700">{appt.doctor?.full_name ?? 'Лікар'}</p>
                  <p className="text-sm text-gray-500">
                    {format(new Date(appt.slot_datetime), 'dd.MM.yyyy, HH:mm')}
                  </p>
                </div>
                <StatusBadge value={appt.status} />
              </div>
            ))}
          </div>
        </section>
      )}

      <ConfirmDialog
        isOpen={!!cancelId}
        title="Скасувати запис?"
        message="Ви впевнені, що хочете скасувати цей запис до лікаря?"
        confirmLabel="Скасувати запис"
        onConfirm={() => cancelId && cancelMutation.mutate(cancelId)}
        onCancel={() => setCancelId(null)}
        danger
      />
    </div>
  )
}
