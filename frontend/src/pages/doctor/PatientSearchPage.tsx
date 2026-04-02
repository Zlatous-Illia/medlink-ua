import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Search, Plus, User } from 'lucide-react'
import { format } from 'date-fns'
import { patientsApi } from '../../api/patients'
import { PageLoading } from '../../components/shared/LoadingSpinner'
import { EmptyState } from '../../components/shared/EmptyState'

export function PatientSearchPage() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')

  const { data: patients, isLoading } = useQuery({
    queryKey: ['patients', search],
    queryFn: () => patientsApi.list({ search: search || undefined, limit: 50 }).then(r => r.data),
  })

  const genderLabel = { MALE: 'Чол.', FEMALE: 'Жін.', OTHER: 'Ін.' }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Пацієнти</h1>
        <button onClick={() => navigate('/doctor/patients/new')} className="btn-primary btn">
          <Plus className="h-4 w-4" />
          Новий пацієнт
        </button>
      </div>

      <div className="relative mb-4">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
        <input
          type="text"
          className="input pl-10"
          placeholder="Пошук за ПІБ, ІПН або телефоном…"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>

      {isLoading ? (
        <PageLoading />
      ) : !patients?.length ? (
        <div className="card p-4">
          <EmptyState message="Пацієнтів не знайдено" />
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="px-4 py-3 text-left font-medium text-gray-600">ПІБ</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">ІПН</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Дата народж.</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Стать</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Телефон</th>
              </tr>
            </thead>
            <tbody>
              {patients.map(p => (
                <tr
                  key={p.id}
                  className="border-b border-gray-50 hover:bg-blue-50 cursor-pointer transition-colors"
                  onClick={() => navigate(`/doctor/patients/${p.id}`)}
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="flex h-7 w-7 items-center justify-center rounded-full bg-gray-100">
                        <User className="h-3.5 w-3.5 text-gray-500" />
                      </div>
                      <span className="font-medium text-gray-900">
                        {p.last_name} {p.first_name} {p.middle_name ?? ''}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-600 font-mono text-xs">{p.tax_id}</td>
                  <td className="px-4 py-3 text-gray-600">
                    {format(new Date(p.birth_date), 'dd.MM.yyyy')}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{genderLabel[p.gender]}</td>
                  <td className="px-4 py-3 text-gray-600">{p.phone ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
