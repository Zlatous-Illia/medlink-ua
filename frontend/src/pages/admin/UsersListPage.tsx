import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'
import { Search } from 'lucide-react'
import { adminApi } from '../../api/admin'
import { StatusBadge } from '../../components/shared/StatusBadge'
import { PageLoading } from '../../components/shared/LoadingSpinner'
import { EmptyState } from '../../components/shared/EmptyState'
import type { UserRole } from '../../api/types'

const ROLES: { value: UserRole | ''; label: string }[] = [
  { value: '', label: 'Всі ролі' },
  { value: 'DOCTOR', label: 'Лікарі' },
  { value: 'PATIENT', label: 'Пацієнти' },
  { value: 'ADMIN', label: 'Адміни' },
  { value: 'SUPER_ADMIN', label: 'Супер-адміни' },
]

export function UsersListPage() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [role, setRole] = useState<UserRole | ''>('')
  const [isActive, setIsActive] = useState<'' | 'true' | 'false'>('')

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

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Користувачі</h1>

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
    </div>
  )
}
