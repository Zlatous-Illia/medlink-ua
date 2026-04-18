import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { format } from 'date-fns'
import { Calendar, Pill, Stethoscope, ArrowRight, UserX, FileText } from 'lucide-react'
import { cabinetApi } from '../../api/patientCabinet'
import { useAuthStore } from '../../store/authStore'
import { PageLoading } from '../../components/shared/LoadingSpinner'
import { StatusBadge } from '../../components/shared/StatusBadge'

export function PatientDashboard() {
  const user = useAuthStore(s => s.user)
  const navigate = useNavigate()

  const { data: prescriptions, isLoading: rxLoading, isError: rxError } = useQuery({
    queryKey: ['my-prescriptions', 'ACTIVE'],
    queryFn: () => cabinetApi.getPrescriptions('ACTIVE').then(r => r.data),
    retry: false,
  })

  const { data: encounters, isLoading: encLoading, isError: encError } = useQuery({
    queryKey: ['my-encounters'],
    queryFn: () => cabinetApi.getEncounters().then(r => r.data),
    retry: false,
  })

  if (rxLoading || encLoading) return <PageLoading />

  if (rxError || encError) {
    return (
      <div>
        <h1 className="text-2xl font-bold text-gray-900 mb-6">
          Вітаємо, {user?.first_name}!
        </h1>
        <div className="card p-8 text-center">
          <div className="flex justify-center mb-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-yellow-100">
              <UserX className="h-7 w-7 text-yellow-600" />
            </div>
          </div>
          <h2 className="text-lg font-semibold text-gray-900 mb-2">
            Профіль пацієнта не прив'язано
          </h2>
          <p className="text-sm text-gray-500">
            Ваш обліковий запис ще не пов'язано з медичною карткою пацієнта.
            Зверніться до лікаря або адміністратора для прив'язки.
          </p>
        </div>
      </div>
    )
  }

  const lastEncounter = encounters?.[0]
  const activeRxCount = prescriptions?.length ?? 0

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">
        Вітаємо, {user?.first_name}!
      </h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="card p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-green-100">
              <Pill className="h-5 w-5 text-green-600" />
            </div>
            <p className="text-sm font-medium text-gray-600">Активні рецепти</p>
          </div>
          <p className="text-3xl font-bold text-gray-900">{activeRxCount}</p>
          <button
            onClick={() => navigate('/patient/prescriptions')}
            className="mt-3 flex items-center gap-1 text-sm text-blue-600 hover:underline"
          >
            Переглянути <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>

        <div className="card p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-100">
              <Stethoscope className="h-5 w-5 text-blue-600" />
            </div>
            <p className="text-sm font-medium text-gray-600">Останній прийом</p>
          </div>
          {lastEncounter ? (
            <>
              <p className="text-sm font-medium text-gray-900">{lastEncounter.doctor_full_name}</p>
              <p className="text-xs text-gray-500 mt-1">
                {format(new Date(lastEncounter.started_at), 'dd.MM.yyyy')}
              </p>
            </>
          ) : (
            <p className="text-sm text-gray-400">Прийомів не було</p>
          )}
          <button
            onClick={() => navigate('/patient/encounters')}
            className="mt-3 flex items-center gap-1 text-sm text-blue-600 hover:underline"
          >
            Всі прийоми <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>

        <div className="card p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-amber-100">
              <FileText className="h-5 w-5 text-amber-600" />
            </div>
            <p className="text-sm font-medium text-gray-600">Мої направлення</p>
          </div>
          <p className="text-sm text-gray-500">Переглядайте активні та минулі направлення до спеціалістів</p>
          <button
            onClick={() => navigate('/patient/referrals')}
            className="mt-3 flex items-center gap-1 text-sm text-blue-600 hover:underline"
          >
            Переглянути <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>

        <div className="card p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-purple-100">
              <Calendar className="h-5 w-5 text-purple-600" />
            </div>
            <p className="text-sm font-medium text-gray-600">Записатись</p>
          </div>
          <p className="text-sm text-gray-500">Оберіть лікаря та зручний час</p>
          <button
            onClick={() => navigate('/patient/appointments/book')}
            className="mt-3 btn-primary btn-sm btn"
          >
            Записатись
          </button>
        </div>
      </div>

      {prescriptions && prescriptions.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Активні рецепти</h2>
          <div className="card overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50">
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Препарат</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Дозування</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Статус</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Дійсний до</th>
                </tr>
              </thead>
              <tbody>
                {prescriptions.slice(0, 5).map(rx => (
                  <tr key={rx.id} className="border-b border-gray-50">
                    <td className="px-4 py-3 font-medium">{rx.drug.inn}</td>
                    <td className="px-4 py-3 text-gray-600">{rx.dosage ?? '—'}</td>
                    <td className="px-4 py-3"><StatusBadge value={rx.status} /></td>
                    <td className="px-4 py-3 text-gray-500">
                      {rx.expires_at ? format(new Date(rx.expires_at), 'dd.MM.yyyy') : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
