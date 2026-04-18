import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { format } from 'date-fns'
import { Search, UserPlus, X } from 'lucide-react'
import { adminApi } from '../../api/admin'
import { StatusBadge } from '../../components/shared/StatusBadge'
import { PageLoading } from '../../components/shared/LoadingSpinner'
import { EmptyState } from '../../components/shared/EmptyState'
import { toast } from '../../components/shared/Toast'
import type { UserRole } from '../../api/types'

const ROLES: { value: UserRole | ''; label: string }[] = [
  { value: '', label: 'Всі ролі' },
  { value: 'DOCTOR', label: 'Лікарі' },
  { value: 'PATIENT', label: 'Пацієнти' },
  { value: 'ADMIN', label: 'Адміни' },
  { value: 'SUPER_ADMIN', label: 'Супер-адміни' },
]

const ALL_ROLES: { value: UserRole; label: string }[] = [
  { value: 'PATIENT', label: 'Пацієнт' },
  { value: 'DOCTOR', label: 'Лікар' },
  { value: 'ADMIN', label: 'Адмін' },
  { value: 'SUPER_ADMIN', label: 'Супер-адмін' },
]

const GENDERS = [
  { value: '', label: 'Не вказано' },
  { value: 'MALE', label: 'Чоловіча' },
  { value: 'FEMALE', label: 'Жіноча' },
  { value: 'OTHER', label: 'Інша' },
]

const emptyForm = {
  email: '', password: '', role: 'PATIENT' as UserRole,
  first_name: '', last_name: '', middle_name: '', phone: '',
  tax_id: '', birth_date: '', gender: '',
}

export function UsersListPage() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [search, setSearch] = useState('')
  const [role, setRole] = useState<UserRole | ''>('')
  const [isActive, setIsActive] = useState<'' | 'true' | 'false'>('')
  const [showModal, setShowModal] = useState(false)
  const [form, setForm] = useState({ ...emptyForm })
  const [formError, setFormError] = useState('')

  const { data: users, isLoading } = useQuery({
    queryKey: ['admin-users', search, role, isActive],
    queryFn: () =>
      adminApi.listUsers({
        search: search || undefined,
        role: (role || undefined) as UserRole | undefined,
        is_active: isActive === '' ? undefined : isActive === 'true',
        limit: 100,
      }).then(r => r.data),
  })

  const createMutation = useMutation({
    mutationFn: () => adminApi.createUser({
      ...form,
      gender: form.gender || undefined,
      middle_name: form.middle_name || undefined,
      phone: form.phone || undefined,
      tax_id: form.tax_id || undefined,
      birth_date: form.birth_date || undefined,
    }),
    onSuccess: (res) => {
      toast('success', 'Користувача створено')
      qc.invalidateQueries({ queryKey: ['admin-users'] })
      setShowModal(false)
      setForm({ ...emptyForm })
      navigate(`/admin/users/${res.data.id}`)
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setFormError(msg || 'Помилка створення')
    },
  })

  function f(key: keyof typeof form, val: string) {
    setForm(prev => ({ ...prev, [key]: val }))
    setFormError('')
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Користувачі</h1>
        <button className="btn-primary btn-sm btn" onClick={() => { setShowModal(true); setForm({ ...emptyForm }); setFormError('') }}>
          <UserPlus className="h-4 w-4" />
          Створити користувача
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            className="input pl-9"
            placeholder="Пошук за email, ПІБ…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <select className="input w-40" value={role} onChange={e => setRole(e.target.value as UserRole | '')}>
          {ROLES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
        </select>
        <select className="input w-40" value={isActive} onChange={e => setIsActive(e.target.value as typeof isActive)}>
          <option value="">Всі статуси</option>
          <option value="true">Активні</option>
          <option value="false">Деактивовані</option>
        </select>
      </div>

      {isLoading ? (
        <PageLoading />
      ) : !users?.length ? (
        <div className="card p-4"><EmptyState message="Користувачів не знайдено" /></div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="px-4 py-3 text-left font-medium text-gray-600">Email</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">ПІБ</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Роль</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Статус</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Реєстрація</th>
              </tr>
            </thead>
            <tbody>
              {users.map(u => (
                <tr
                  key={u.id}
                  className="border-b border-gray-50 hover:bg-blue-50 cursor-pointer transition-colors"
                  onClick={() => navigate(`/admin/users/${u.id}`)}
                >
                  <td className="px-4 py-3 text-gray-900 font-medium">{u.email}</td>
                  <td className="px-4 py-3 text-gray-700">
                    {u.last_name} {u.first_name} {u.middle_name ?? ''}
                  </td>
                  <td className="px-4 py-3"><StatusBadge value={u.role} /></td>
                  <td className="px-4 py-3">
                    <span className={`badge ${u.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                      {u.is_active ? 'Активний' : 'Деактивований'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500">
                    {format(new Date(u.created_at), 'dd.MM.yyyy')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create user modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="card w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-semibold text-gray-900">Створити користувача</h2>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-gray-600">
                <X className="h-5 w-5" />
              </button>
            </div>

            {formError && (
              <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
                {formError}
              </div>
            )}

            <div className="space-y-3">
              <div>
                <label className="label">Роль *</label>
                <select className="input" value={form.role} onChange={e => f('role', e.target.value)}>
                  {ALL_ROLES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
                </select>
              </div>

              <div>
                <label className="label">Email *</label>
                <input type="email" className="input" value={form.email} onChange={e => f('email', e.target.value)} />
              </div>

              <div>
                <label className="label">Пароль *</label>
                <input type="password" className="input" placeholder="Мін. 8 символів, велика літера, цифра"
                  value={form.password} onChange={e => f('password', e.target.value)} />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label">Прізвище *</label>
                  <input className="input" value={form.last_name} onChange={e => f('last_name', e.target.value)} />
                </div>
                <div>
                  <label className="label">Ім'я *</label>
                  <input className="input" value={form.first_name} onChange={e => f('first_name', e.target.value)} />
                </div>
              </div>

              <div>
                <label className="label">По батькові</label>
                <input className="input" value={form.middle_name} onChange={e => f('middle_name', e.target.value)} />
              </div>

              <div>
                <label className="label">Телефон</label>
                <input className="input" placeholder="+380XXXXXXXXX" value={form.phone} onChange={e => f('phone', e.target.value)} />
              </div>

              {form.role === 'PATIENT' && (
                <>
                  <div>
                    <label className="label">РНОКПП (ІПН)</label>
                    <input className="input" maxLength={10} value={form.tax_id} onChange={e => f('tax_id', e.target.value)} />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="label">Дата народження</label>
                      <input type="date" className="input" value={form.birth_date} onChange={e => f('birth_date', e.target.value)} />
                    </div>
                    <div>
                      <label className="label">Стать</label>
                      <select className="input" value={form.gender} onChange={e => f('gender', e.target.value)}>
                        {GENDERS.map(g => <option key={g.value} value={g.value}>{g.label}</option>)}
                      </select>
                    </div>
                  </div>
                </>
              )}
            </div>

            <div className="flex gap-2 mt-5">
              <button
                className="btn-primary btn-sm btn flex-1"
                disabled={createMutation.isPending}
                onClick={() => createMutation.mutate()}
              >
                {createMutation.isPending ? 'Створення…' : 'Створити'}
              </button>
              <button className="btn-secondary btn-sm btn" onClick={() => setShowModal(false)}>
                Скасувати
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}