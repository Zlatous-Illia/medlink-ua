import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'
import { ExternalLink, FileText } from 'lucide-react'
import { cabinetApi } from '../../api/patientCabinet'
import { PageLoading } from '../../components/shared/LoadingSpinner'
import { EmptyState } from '../../components/shared/EmptyState'
import { StatusBadge } from '../../components/shared/StatusBadge'

export function MyReferralsPage() {
  const { data: referrals, isLoading, isError } = useQuery({
    queryKey: ['my-referrals'],
    queryFn: () => cabinetApi.getReferrals().then(r => r.data),
    retry: false,
  })

  if (isLoading) return <PageLoading />

  if (isError) {
    return (
      <div>
        <h1 className="text-2xl font-bold text-gray-900 mb-6">Мої направлення</h1>
        <div className="card p-6 text-center text-gray-500">
          Профіль пацієнта не прив'язано до акаунту. Зверніться до лікаря або адміністратора.
        </div>
      </div>
    )
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Мої направлення</h1>

      {!referrals?.length ? (
        <div className="card p-4"><EmptyState message="Направлень не знайдено" /></div>
      ) : (
        <div className="space-y-3">
          {referrals.map(ref => (
            <div key={ref.id} className="card p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <StatusBadge value={ref.status} />
                    <span className="text-sm font-medium text-gray-900">{ref.doctor_full_name}</span>
                    {ref.specialization_name && (
                      <span className="text-xs text-gray-500">• {ref.specialization_name}</span>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 mb-3">
                    {format(new Date(ref.created_at), 'dd.MM.yyyy HH:mm')}
                    {ref.expires_at && ` — дійсне до ${format(new Date(ref.expires_at), 'dd.MM.yyyy')}`}
                  </p>

                  {ref.reason && <p className="text-sm text-gray-700 mb-3">{ref.reason}</p>}

                  <div className="flex flex-wrap gap-3 text-xs text-gray-500">
                    {ref.esoz_referral_id && (
                      <span className="flex items-center gap-1.5">
                        <ExternalLink className="h-3.5 w-3.5" />
                        ЕСОЗ ID: <span className="font-mono">{ref.esoz_referral_id}</span>
                      </span>
                    )}
                    <span className="flex items-center gap-1.5">
                      <FileText className="h-3.5 w-3.5" />
                      Прийом: <span className="font-mono">{ref.encounter_id.slice(0, 8)}</span>
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

