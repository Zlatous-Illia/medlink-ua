import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { format, subDays } from 'date-fns'
import {
  LineChart, Line, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts'
import { Users, UserCheck, Stethoscope, Pill, Calendar } from 'lucide-react'
import { adminApi } from '../../api/admin'
import { analyticsApi } from '../../api/analytics'
import { PageLoading } from '../../components/shared/LoadingSpinner'

const DEFAULT_FROM = format(subDays(new Date(), 90), 'yyyy-MM-dd')

function StatCard({ icon: Icon, label, value, sub, color }: {
  icon: React.ElementType; label: string; value: number; sub?: string; color: string
}) {
  return (
    <div className="card p-5">
      <div className="flex items-center gap-3 mb-3">
        <div className={`flex h-10 w-10 items-center justify-center rounded-full ${color}`}>
          <Icon className="h-5 w-5" />
        </div>
        <p className="text-sm text-gray-500">{label}</p>
      </div>
      <p className="text-3xl font-bold text-gray-900">{value.toLocaleString()}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  )
}

export function AdminDashboard() {
  const [dateFrom] = useState(DEFAULT_FROM)

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['admin-stats'],
    queryFn: () => adminApi.getStats().then(r => r.data),
  })

  const { data: apptData } = useQuery({
    queryKey: ['analytics-appointments', dateFrom],
    queryFn: () => analyticsApi.appointments({ date_from: dateFrom, group_by: 'month' }).then(r => r.data),
  })

  const { data: diagData } = useQuery({
    queryKey: ['analytics-diagnoses', dateFrom],
    queryFn: () => analyticsApi.topDiagnoses({ date_from: dateFrom }).then(r => r.data),
  })

  const { data: loadData } = useQuery({
    queryKey: ['analytics-load', dateFrom],
    queryFn: () => analyticsApi.doctorLoad({ date_from: dateFrom }).then(r => r.data),
  })

  const { data: cancelData } = useQuery({
    queryKey: ['analytics-cancel', dateFrom],
    queryFn: () => analyticsApi.cancellationRate({ date_from: dateFrom }).then(r => r.data),
  })

  if (statsLoading) return <PageLoading />

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Дашборд адміністратора</h1>

      {/* Stats cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
        <StatCard
          icon={Users}
          label="Всього користувачів"
          value={stats?.users.total ?? 0}
          sub={`Лікарів: ${stats?.users.by_role?.DOCTOR ?? 0}`}
          color="bg-blue-100 text-blue-600"
        />
        <StatCard
          icon={UserCheck}
          label="Пацієнтів"
          value={stats?.patients.total ?? 0}
          sub={`Активних: ${stats?.patients.active ?? 0}`}
          color="bg-teal-100 text-teal-600"
        />
        <StatCard
          icon={Stethoscope}
          label="Прийомів"
          value={stats?.encounters.total ?? 0}
          sub={`За 30 дн: ${stats?.encounters.last_30_days ?? 0}`}
          color="bg-purple-100 text-purple-600"
        />
        <StatCard
          icon={Pill}
          label="Рецептів"
          value={stats?.prescriptions.total ?? 0}
          sub={`Активних: ${stats?.prescriptions.active ?? 0}`}
          color="bg-green-100 text-green-600"
        />
        <StatCard
          icon={Calendar}
          label="Записів"
          value={stats?.appointments.total ?? 0}
          sub={`Майбутніх: ${stats?.appointments.upcoming ?? 0}`}
          color="bg-orange-100 text-orange-600"
        />
      </div>

      {/* Charts grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Appointments by month */}
        <div className="card p-5">
          <h3 className="font-semibold text-gray-900 mb-4">Записи по місяцях</h3>
          {apptData?.length ? (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={apptData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="period" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="total" stroke="#3b82f6" name="Всього" strokeWidth={2} />
                <Line type="monotone" dataKey="completed" stroke="#10b981" name="Завершено" strokeWidth={2} />
                <Line type="monotone" dataKey="cancelled" stroke="#ef4444" name="Скасовано" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[220px] flex items-center justify-center text-gray-400 text-sm">Немає даних</div>
          )}
        </div>

        {/* Top-10 diagnoses */}
        <div className="card p-5">
          <h3 className="font-semibold text-gray-900 mb-4">Топ-10 діагнозів</h3>
          {diagData?.length ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={diagData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="icd10_code" tick={{ fontSize: 11 }} width={60} />
                <Tooltip formatter={(v, _n, p) => [v, p.payload.name_ua]} />
                <Bar dataKey="count" fill="#6366f1" name="Кількість" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[220px] flex items-center justify-center text-gray-400 text-sm">Немає даних</div>
          )}
        </div>

        {/* Doctor load */}
        <div className="card p-5">
          <h3 className="font-semibold text-gray-900 mb-4">Навантаження лікарів</h3>
          {loadData?.length ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={loadData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="full_name" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="encounters_count" fill="#3b82f6" name="Прийомів" radius={[4, 4, 0, 0]} />
                <Bar dataKey="appointments_count" fill="#10b981" name="Записів" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[220px] flex items-center justify-center text-gray-400 text-sm">Немає даних</div>
          )}
        </div>

        {/* Cancellation rate */}
        <div className="card p-5">
          <h3 className="font-semibold text-gray-900 mb-4">Відсоток скасувань</h3>
          {cancelData ? (
            <div className="flex flex-col items-center justify-center h-[220px] gap-3">
              <div className="text-6xl font-bold text-gray-900">
                {cancelData.cancellation_rate.toFixed(1)}%
              </div>
              <p className="text-sm text-gray-500">
                {cancelData.cancelled} з {cancelData.total_appointments} записів
              </p>
              <div className="w-full bg-gray-100 rounded-full h-3 mt-2">
                <div
                  className="bg-red-500 h-3 rounded-full transition-all"
                  style={{ width: `${Math.min(cancelData.cancellation_rate, 100)}%` }}
                />
              </div>
            </div>
          ) : (
            <div className="h-[220px] flex items-center justify-center text-gray-400 text-sm">Немає даних</div>
          )}
        </div>
      </div>
    </div>
  )
}
