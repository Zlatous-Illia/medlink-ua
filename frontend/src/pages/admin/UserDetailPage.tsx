import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { format } from 'date-fns'
import { ArrowLeft, ShieldAlert, Power, Edit2, Trash2 } from 'lucide-react'
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
  const canDelete = isSuperAdmin || currentUser?.role === 'ADMIN'
  const [confirmDeactivate, setConfirmDeactivate] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [editingProfile, setEditingProfile] = useState(false)
  const [profileForm, setProfileForm] = useState({
    first_name: '', last_name: '', middle_name: '', phone: '', email: '',
  })

  const { data: user, isLoading } = useQuery({
    queryKey: ['admin-user', id],
    queryFn: () => adminApi.getUser(id!).then(r => r.data),
    enabled: !!id,
  })

  const updateMutation = useMutation({
    mutationFn: (data: Parameters<typeof adminApi.updateUser>[1]) =>
      adminApi.updateUser(id!, data),
    onSuccess: () => {
      toast('success', 'Зміни збережено')
      setEditingProfile(false)
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

  const deleteMutation = useMutation({
    mutationFn: () => adminApi.deleteUser(id!),
    onSuccess: () => {
      toast('success', 'Користувача видалено')
      navigate('/admin/users')
    },
    onError: () => toast('error', 'Помилка видалення'),
  })

  function openEditProfile() {
    if (!user) return
    setProfileForm({
      first_name: user.first_name,
      last_name: user.last_name,
      middle_name: user.middle_name ?? '',
      phone: user.phone ?? '',
      email: user.email,
    })
    setEditingProfile(true)
  }

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
            <div className="flex items-center gap-2">
              <span className={`badge ${user.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                {user.is_active ? 'Активний' : 'Деактивований'}
              </span>
              {!editingProfile && (
                <button onClick={openEditProfile} className="btn-secondary btn-sm btn">
                  <Edit2 className="h-3.5 w-3.5" />
                  Редагувати
                </button>
              )}
            </div>
          </div>

          {editingProfile ? (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label">Прізвище</label>
                  <input className="input" value={profileForm.last_name}
                    onChange={e => setProfileForm(f => ({ ...f, last_name: e.target.value }))} />
                </div>
                <div>
                  <label className="label">Ім'я</label>
                  <input className="input" value={profileForm.first_name}
                    onChange={e => setProfileForm(f => ({ ...f, first_name: e.target.value }))} />
                </div>
                <div>
                  <label className="label">По батькові</label>
                  <input className="input" value={profileForm.middle_name}
                    onChange={e => setProfileForm(f => ({ ...f, middle_name: e.target.value }))} />
                </div>
                <div>
                  <label className="label">Телефон</label>
                  <input className="input" value={profileForm.phone}
                    onChange={e => setProfileForm(f => ({ ...f, phone: e.target.value }))} />
                </div>
                <div className="col-span-2">
                  <label className="label">Email</label>
                  <input className="input" type="email" value={profileForm.email}
                    onChange={e => setProfileForm(f => ({ ...f, email: e.target.value }))} />
                </div>
              </div>
              <div className="flex gap-2">
                <button className="btn-primary btn-sm btn" disabled={updateMutation.isPending}
                  onClick={() => updateMutation.mutate(profileForm)}>
                  Зберегти
                </button>
                <button className="btn-secondary btn-sm btn" onClick={() => setEditingProfile(false)}>
                  Скасувати
                </button>
              </div>
            </div>
          ) : (
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
          )}
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

        {/* Delete */}
        {canDelete && (
          <div className="card p-5 border-red-200">
            <div className="flex items-center gap-2 mb-3">
              <Trash2 className="h-4 w-4 text-red-600" />
              <h3 className="font-semibold text-red-700">Видалити користувача</h3>
            </div>
            <p className="text-sm text-gray-500 mb-3">
              Незворотна дія. Всі дані користувача будуть видалені з системи.
            </p>
            <button onClick={() => setConfirmDelete(true)} className="btn-danger btn-sm btn">
              Видалити назавжди
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

      <ConfirmDialog
        isOpen={confirmDelete}
        title="Видалити користувача?"
        message={`Ви впевнені, що хочете видалити ${user.first_name} ${user.last_name}? Цю дію неможливо скасувати.`}
        confirmLabel="Видалити"
        onConfirm={() => deleteMutation.mutate()}
        onCancel={() => setConfirmDelete(false)}
        danger
      />
    </div>
  )
}
