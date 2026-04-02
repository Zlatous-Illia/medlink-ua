import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'
import { Search, Filter } from 'lucide-react'
import { adminApi } from '../../api/admin'
import { PageLoading } from '../../components/shared/LoadingSpinner'
import { EmptyState } from '../../components/shared/EmptyState'

export function AuditLogPage() {
  const [action, setAction] = useState('')
  const [resource, setResource] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  const { data: logs, isLoading } = useQuery({
    queryKey: ['audit-logs', action, resource, dateFrom, dateTo],
    queryFn: () =>
      adminApi.getAuditLogs({
        action: action || undefined,
        resource: resource || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        limit: 100,
      }).then(r => r.data),
  })

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Журнал дій</h1>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <div className="relative min-w-36">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            className="input pl-9"
            placeholder="Дія (LOGIN…)"
            value={action}
            onChange={e => setAction(e.target.value)}
          />
        </div>
        <div className="relative min-w-36">
          <Filter className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            className="input pl-9"
            placeholder="Ресурс"
            value={resource}
            onChange={e => setResource(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-2">
          <input type="date" className="input" value={dateFrom} onChange={e => setDateFrom(e.target.value)} />
          <span className="text-gray-400 text-sm">—</span>
          <input type="date" className="input" value={dateTo} onChange={e => setDateTo(e.target.value)} />
        </div>
      </div>

      {isLoading ? (
        <PageLoading />
      ) : !logs?.length ? (
        <div className="card p-4"><EmptyState message="Записів не знайдено" /></div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="px-4 py-3 text-left font-medium text-gray-600">Час</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Дія</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Ресурс</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">IP адреса</th>
              </tr>
            </thead>
            <tbody>
              {logs.map(log => (
                <tr key={log.id} className="border-b border-gray-50">
                  <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
                    {format(new Date(log.created_at), 'dd.MM.yyyy HH:mm:ss')}
                  </td>
                  <td className="px-4 py-3">
                    <span className="badge bg-blue-50 text-blue-700 font-mono text-xs">
                      {log.action}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {log.resource ?? '—'}
                    {log.resource_id && (
                      <span className="text-gray-400 font-mono text-xs ml-1">
                        #{log.resource_id.slice(0, 8)}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-500 font-mono text-xs">
                    {log.ip_address ?? '—'}
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
