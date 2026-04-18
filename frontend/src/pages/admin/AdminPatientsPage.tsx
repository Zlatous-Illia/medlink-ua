import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { format } from 'date-fns'
import { Search, ExternalLink, Trash2 } from 'lucide-react'
import { patientsApi } from '../../api/patients'
import { PageLoading } from '../../components/shared/LoadingSpinner'
import { EmptyState } from '../../components/shared/EmptyState'
import { ConfirmDialog } from '../../components/shared/ConfirmDialog'
import { toast } from '../../components/shared/Toast'

const GENDER_LABELS: Record<string, string> = { MALE: 'Чол.', FEMALE: 'Жін.', OTHER: 'Інше' }

export function AdminPatientsPage() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const debounceRef = useRef<ReturnType<typeof setTimeout>>()
  const [confirmId, setConfirmId] = useState<string | null>(null)
  const [confirmName, setConfirmName] = useState('')

  function handleSearch(val: string) {
    setSearch(val)
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => setDebouncedSearch(val), 300)
  }

  const { data: patients, isLoading } = useQuery({
    queryKey: ['admin-patients', debouncedSearch],
    queryFn: () => patientsApi.list({ search: debouncedSearch || undefined, limit: 100 }).then(r => r.data),
  })

  const deactivateMutation = useMutation({
    mutationFn: (id: string) => patientsApi.deactivate(id),
    onSuccess: () => {
      toast('success', 'Пацієнта деактивовано')
      qc.invalidateQueries({ queryKey: ['admin-patients'] })
      setConfirmId(null)
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast('error', msg || 'Помилка деактивації')
      setConfirmId(null)
    },
  })

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Пацієнти</h1>
        <span className="text-sm text-gray-500">{patients?.length ?? 0} записів</span>
      </div>

      <div className="card p-4 mb-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            className="input pl-9"
            placeholder="Пошук за ПІБ, ІПН, телефоном…"
            value={search}
            onChange={e => handleSearch(e.target.value)}
          />
        </div>
      </div>

      {isLoading ? (
        <PageLoading />
      ) : !patients?.length ? (
        <div className="card p-4"><EmptyState message="Пацієнтів не знайдено" /></div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="px-4 py-3 text-left font-medium text-gray-600">ПІБ</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">ІПН</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Стать</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Дата народж.</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Телефон</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Статус</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {patients.map(p => (
                <tr key={p.id} className="border-b border-gray-50 hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">
                    {p.last_name} {p.first_name} {p.middle_name ?? ''}
                  </td>
                  <td className="px-4 py-3 font-mono text-gray-600">{p.tax_id}</td>
                  <td className="px-4 py-3 text-gray-600">{GENDER_LABELS[p.gender] ?? p.gender}</td>
                  <td className="px-4 py-3 text-gray-600">
                    {format(new Date(p.birth_date), 'dd.MM.yyyy')}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{p.phone ?? '—'}</td>
                  <td className="px-4 py-3">
                    <span className={`badge text-xs ${p.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                      {p.is_active ? 'Активний' : 'Неактивний'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-2">
                      <button
                        className="btn-secondary btn-sm btn"
                        onClick={() => navigate(`/admin/patients/${p.id}`)}
                      >
                        <ExternalLink className="h-3.5 w-3.5" />
                        ЕМК
                      </button>
                      {/* Show deactivate only for unlinked patients that are still active */}
                      {!p.user_id && p.is_active && (
                        <button
                          className="btn-danger btn-sm btn"
                          onClick={() => {
                            setConfirmId(p.id)
                            setConfirmName(`${p.last_name} ${p.first_name}`)
                          }}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <ConfirmDialog
        isOpen={!!confirmId}
        title="Деактивувати пацієнта?"
        message={`${confirmName} — запис буде деактивовано. Медичні дані збережуться.`}
        confirmLabel="Деактивувати"
        onConfirm={() => confirmId && deactivateMutation.mutate(confirmId)}
        onCancel={() => setConfirmId(null)}
        danger
      />
    </div>
  )
}