import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'
import { FileText } from 'lucide-react'
import { cabinetApi } from '../../api/patientCabinet'
import { StatusBadge } from '../../components/shared/StatusBadge'
import { PageLoading } from '../../components/shared/LoadingSpinner'
import { EmptyState } from '../../components/shared/EmptyState'

const DIAG_TYPE_LABELS = { MAIN: 'Осн.', COMPLICATION: 'Ускл.', CONCOMITANT: 'Суп.' }

export function MyEncountersPage() {
  const { data: encounters, isLoading, isError } = useQuery({
    queryKey: ['my-encounters'],
    queryFn: () => cabinetApi.getEncounters().then(r => r.data),
    retry: false,
  })

  if (isLoading) return <PageLoading />
  if (isError) return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Мої прийоми</h1>
      <div className="card p-6 text-center text-gray-500">
        Профіль пацієнта не прив'язано до акаунту. Зверніться до адміністратора.
      </div>
    </div>
  )

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Мої прийоми</h1>

      {!encounters?.length ? (
        <div className="card p-4"><EmptyState message="Прийомів не знайдено" /></div>
      ) : (
        <div className="space-y-3">
          {encounters.map(enc => (
            <div key={enc.id} className="card p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <StatusBadge value={enc.status} />
                    <span className="text-sm font-medium text-gray-900">
                      {enc.doctor_full_name}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mb-3">
                    {format(new Date(enc.started_at), 'dd.MM.yyyy HH:mm')}
                    {enc.completed_at && ` — ${format(new Date(enc.completed_at), 'HH:mm')}`}
                  </p>

                  {enc.diagnoses.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {enc.diagnoses.map((d, i) => (
                        <span
                          key={i}
                          className="badge bg-gray-100 text-gray-600 text-xs"
                          title={DIAG_TYPE_LABELS[d.type]}
                        >
                          {d.code} — {d.name_ua}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {enc.pdf_url && (
                  <a
                    href={enc.pdf_url}
                    target="_blank"
                    rel="noreferrer"
                    className="btn-secondary btn-sm btn shrink-0"
                  >
                    <FileText className="h-3.5 w-3.5" />
                    PDF виписка
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
