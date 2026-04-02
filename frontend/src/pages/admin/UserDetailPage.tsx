import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { format } from 'date-fns'
import { ArrowLeft, ShieldAlert, Power } from 'lucide-react'
import { adminApi } from '../../api/admin'
import { useAuthStore } from '../../store/authStore'
import { StatusBadge } from '../../components/shared/StatusBadge'
import { ConfirmDialog } from '../../components/shared/ConfirmDialog'
import { PageLoading } from '../../components/shared/LoadingSpinner'
import { toast } from '../../components/shared/Toast'
import type { UserRole } from '../../api/types'

const ALL_ROLES: UserRole[] = ['PATIENT', 'DOCTOR', 'ADMIN', 'SUPER_ADMIN']
const ROLE_LABELS: Record<UserRole, string> = {
  PATIENT: 'Пацієнт', DOCTOR: 'Лікар', ADMIN: 'Адмін', SUPER_ADMIN: 'Супер-адмін',
}

export function UserDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const currentUser = useAuthStore(s => s.user)
  const isSuperAdmin = currentUser?.role === 'SUPER_ADMIN'
  const [confirmDeactivate, setConfirmDeactivate] = useState(false)

  const { data: user, isLoading } = useQuery({
    queryKey: ['admin-user', id],
    queryFn: () => adminApi.getUser(id!).then(r => r.data),
    enabled: !!id,
  })

  const updateMutation = useMutation({
    mutationFn: (data: { is_active?: boolean; role?: UserRole }) =>
      adminApi.updateUser(id!, data),
    onSuccess: () => {
      toast('success', 'Зміни збережено')
      qc.invalidateQueries({ queryKey: ['admin-user', id] })
    },
    onError: () => toast('error', 'Помилка збереження'),
  })

  const deactivateMutation = useMutation({
    mutationFn: () => adminApi.deactivateUser(id!),
    onSuccess: () => {
      toast('success', 'Користувача деактивовано')
      qc.invalidateQueries({ queryKey: ['admin-user', id] })
      setConfirmDeactivate(false)
    },
    onError: () => toast('error', 'Помилка деактивації'),
  })

  if (isLoading) return <PageLoading />
  if (!user) return <p className="text-gray-500">Користувача не знайдено</p>

  return (
    <div className="max-w-xl">
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate(-1)} className="btn-secondary btn-sm btn">
          <ArrowLeft className="h-4 w-4" />
        </button>
        <h1 className="text-2xl font-bold text-gray-900">Деталі користувача</h1>
      </div>

      <div className="space-y-4">
        {/* Info */}
        <div className="card p-5">
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="text-xl font-semibold text-gray-900">
                {user.last_name} {user.first_name} {user.middle_name ?? ''}
              </p>
              <p className="text-sm text-gray-500">{user.email}</p>
              {user.phone && <p className="text-sm text-gray-500">{user.phone}</p>}
            </div>
            <span className={`badge ${user.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
              {user.is_active ? 'Активний' : 'Деактивований'}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-gray-500">Роль</p>
              <StatusBadge value={user.role} />
            </div>
            <div>
              <p className="text-gray-500">Реєстрація</p>
              <p className="font-medium">{format(new Date(user.created_at), 'dd.MM.yyyy')}</p>
            </div>
            <div>
              <p className="text-gray-500">Кількість подій</p>
              <p className="font-medium">{user.audit_events_count}</p>
            </div>
          </div>
        </div>

        {/* Role change (SUPER_ADMIN only) */}
        {isSuperAdmin && (
          <div className="card p-5">
            <div className="flex items-center gap-2 mb-3">
              <ShieldAlert className="h-4 w-4 text-purple-500" />
              <h3 className="font-semibold text-gray-900">Змінити роль</h3>
            </div>
            <select
              className="input"
              value={user.role}
              onChange={e => updateMutation.mutate({ role: e.target.value as UserRole })}
              disabled={updateMutation.isPending}
            >
              {ALL_ROLES.map(r => (
                <option key={r} value={r}>{ROLE_LABELS[r]}</option>
              ))}
            </select>
          </div>
        )}

        {/* Deactivate */}
        {user.is_active && (
          <div className="card p-5">
            <div className="flex items-center gap-2 mb-3">
              <Power className="h-4 w-4 text-red-500" />
              <h3 className="font-semibold text-gray-900">Деактивація</h3>
            </div>
            <p className="text-sm text-gray-500 mb-3">
              Деактивований користувач не зможе увійти в систему. Всі активні сесії будуть завершені.
            </p>
            <button
              onClick={() => setConfirmDeactivate(true)}
              className="btn-danger btn-sm btn"
            >
              Деактивувати користувача
            </button>
          </div>
        )}
      </div>

      <ConfirmDialog
        isOpen={confirmDeactivate}
        title="Деактивувати користувача?"
        message={`${user.first_name} ${user.last_name} не зможе увійти в систему. Всі активні токени будуть анульовані.`}
        confirmLabel="Деактивувати"
        onConfirm={() => deactivateMutation.mutate()}
        onCancel={() => setConfirmDeactivate(false)}
        danger
      />
    </div>
  )
}
