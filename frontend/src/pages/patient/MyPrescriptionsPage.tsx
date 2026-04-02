import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'
import QRCode from 'react-qr-code'
import { cabinetApi } from '../../api/patientCabinet'
import { StatusBadge } from '../../components/shared/StatusBadge'
import { PageLoading } from '../../components/shared/LoadingSpinner'
import { EmptyState } from '../../components/shared/EmptyState'
import type { PrescriptionStatus } from '../../api/types'

const TABS: { label: string; status?: PrescriptionStatus }[] = [
  { label: 'Активні', status: 'ACTIVE' },
  { label: 'Всі', status: undefined },
]

export function MyPrescriptionsPage() {
  const [activeTab, setActiveTab] = useState<typeof TABS[number]>(TABS[0])
  const [expandedQR, setExpandedQR] = useState<string | null>(null)

  const { data: prescriptions, isLoading, isError } = useQuery({
    queryKey: ['my-prescriptions', activeTab.status],
    queryFn: () => cabinetApi.getPrescriptions(activeTab.status).then(r => r.data),
    retry: false,
  })

  if (isLoading) return <PageLoading />
  if (isError) return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-4">Мої рецепти</h1>
      <div className="card p-6 text-center text-gray-500">
        Профіль пацієнта не прив'язано до акаунту. Зверніться до адміністратора.
      </div>
    </div>
  )

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-4">Мої рецепти</h1>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200 mb-6">
        {TABS.map(t => (
          <button
            key={t.label}
            onClick={() => setActiveTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors
              ${activeTab.label === t.label
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {!prescriptions?.length ? (
        <div className="card p-4">
          <EmptyState message="Рецептів не знайдено" />
        </div>
      ) : (
        <div className="grid gap-4">
          {prescriptions.map(rx => (
            <div key={rx.id} className="card p-5">
              <div className="flex items-start gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <p className="font-semibold text-gray-900">{rx.drug.inn}</p>
                    {rx.drug.trade_name && (
                      <span className="text-sm text-gray-500">({rx.drug.trade_name})</span>
                    )}
                    <StatusBadge value={rx.status} />
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm mt-2">
                    {rx.dosage && <p className="text-gray-600"><span className="text-gray-400">Доза:</span> {rx.dosage}</p>}
                    {rx.frequency && <p className="text-gray-600"><span className="text-gray-400">Частота:</span> {rx.frequency}</p>}
                    {rx.duration_days && <p className="text-gray-600"><span className="text-gray-400">Тривалість:</span> {rx.duration_days} дн.</p>}
                    {rx.expires_at && (
                      <p className="text-gray-600">
                        <span className="text-gray-400">Дійсний до:</span>{' '}
                        {format(new Date(rx.expires_at), 'dd.MM.yyyy')}
                      </p>
                    )}
                  </div>

                  {rx.instructions && (
                    <p className="text-sm text-gray-500 mt-2 italic">{rx.instructions}</p>
                  )}

                  <p className="text-xs text-gray-400 mt-2">
                    Виписано: {format(new Date(rx.created_at), 'dd.MM.yyyy')}
                  </p>
                </div>

                {rx.esoz_request_number && (
                  <div className="shrink-0">
                    <button
                      onClick={() => setExpandedQR(expandedQR === rx.id ? null : rx.id)}
                      className="btn-secondary btn-sm btn"
                    >
                      QR-код
                    </button>
                  </div>
                )}
              </div>

              {expandedQR === rx.id && rx.esoz_request_number && (
                <div className="mt-4 flex flex-col items-center gap-2 p-4 bg-gray-50 rounded-lg">
                  <QRCode value={rx.esoz_request_number} size={160} />
                  <p className="text-xs text-gray-500 font-mono">{rx.esoz_request_number}</p>
                  <p className="text-xs text-gray-400">Покажіть QR-код у аптеці</p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
