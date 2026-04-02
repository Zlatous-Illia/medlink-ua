import { useQuery } from '@tanstack/react-query'
import { AlertTriangle } from 'lucide-react'
import { cabinetApi } from '../../api/patientCabinet'
import { PageLoading } from '../../components/shared/LoadingSpinner'

const SEVERITY_COLORS = {
  MILD: 'bg-yellow-100 text-yellow-700',
  MODERATE: 'bg-orange-100 text-orange-700',
  SEVERE: 'bg-red-100 text-red-700',
}
const SEVERITY_LABELS = { MILD: 'Легка', MODERATE: 'Помірна', SEVERE: 'Важка' }

const BLOOD_TYPE_LABELS: Record<string, string> = {
  'A+': 'A (II) Rh+', 'A-': 'A (II) Rh-',
  'B+': 'B (III) Rh+', 'B-': 'B (III) Rh-',
  'AB+': 'AB (IV) Rh+', 'AB-': 'AB (IV) Rh-',
  'O+': '0 (I) Rh+', 'O-': '0 (I) Rh-',
  UNKNOWN: 'Невідома',
}

const HABITS_LABELS: Record<string, string> = {
  NEVER: 'Ні', FORMER: 'Колишній', CURRENT: 'Так', UNKNOWN: '—',
}

function calcBMI(height?: number, weight?: number): string {
  if (!height || !weight) return '—'
  const bmi = weight / ((height / 100) ** 2)
  const label = bmi < 18.5 ? 'Недостатня вага' : bmi < 25 ? 'Норма' : bmi < 30 ? 'Надлишкова вага' : 'Ожиріння'
  return `${bmi.toFixed(1)} (${label})`
}

export function MyMedicalCardPage() {
  const { data: card, isLoading, isError } = useQuery({
    queryKey: ['my-medical-card'],
    queryFn: () => cabinetApi.getMedicalCard().then(r => r.data),
    retry: false,
  })

  if (isLoading) return <PageLoading />

  if (isError) return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Моя медична картка</h1>
      <div className="card p-6 text-center text-gray-500 mt-4">
        Профіль пацієнта не прив'язано до акаунту. Зверніться до лікаря або адміністратора.
      </div>
    </div>
  )

  if (!card) return <p className="text-gray-500">Медкартку не знайдено</p>

  return (
    <div className="max-w-2xl space-y-5">
      <h1 className="text-2xl font-bold text-gray-900">Моя медична картка</h1>
      <p className="text-sm text-gray-500">Тільки для читання. Зміни вносить лікар.</p>

      {/* Vital signs */}
      <div className="card p-5">
        <h3 className="font-semibold text-gray-900 mb-4">Антропометрія та група крові</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {[
            ['Група крові', card.blood_type ? BLOOD_TYPE_LABELS[card.blood_type] ?? card.blood_type : '—'],
            ['Зріст', card.height_cm ? `${card.height_cm} см` : '—'],
            ['Вага', card.weight_kg ? `${card.weight_kg} кг` : '—'],
            ['ІМТ', calcBMI(card.height_cm, card.weight_kg)],
          ].map(([label, val]) => (
            <div key={label} className="text-sm">
              <p className="text-gray-500 mb-1">{label}</p>
              <p className="font-semibold text-gray-900">{val}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Habits & disability */}
      <div className="card p-5">
        <h3 className="font-semibold text-gray-900 mb-4">Спосіб життя та соціальний стан</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
          <div>
            <p className="text-gray-500 mb-1">Тютюнопаління</p>
            <p className="font-semibold text-gray-900">{HABITS_LABELS[card.smoking_status ?? 'UNKNOWN']}</p>
          </div>
          <div>
            <p className="text-gray-500 mb-1">Вживання алкоголю</p>
            <p className="font-semibold text-gray-900">{HABITS_LABELS[card.alcohol_status ?? 'UNKNOWN']}</p>
          </div>
          <div>
            <p className="text-gray-500 mb-1">Група інвалідності</p>
            <p className="font-semibold text-gray-900">{card.disability_group || '—'}</p>
          </div>
        </div>
      </div>

      {/* Allergies */}
      <div className="card p-5">
        <h3 className="font-semibold text-gray-900 mb-3">
          Алергії {card.allergies.length > 0 && `(${card.allergies.length})`}
        </h3>
        {!card.allergies.length ? (
          <p className="text-sm text-gray-400">Алергій не зазначено</p>
        ) : (
          <div className="space-y-2">
            {card.allergies.map(a => (
              <div key={a.id} className="flex items-start gap-3 p-3 rounded-lg border border-orange-100 bg-orange-50">
                <AlertTriangle className="h-4 w-4 text-orange-500 mt-0.5 shrink-0" />
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-900">{a.substance}</span>
                    <span className={`badge ${SEVERITY_COLORS[a.severity]}`}>
                      {SEVERITY_LABELS[a.severity]}
                    </span>
                  </div>
                  {a.reaction && <p className="text-xs text-gray-500 mt-0.5">{a.reaction}</p>}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Chronic diseases */}
      <div className="card p-5">
        <h3 className="font-semibold text-gray-900 mb-3">
          Хронічні захворювання {card.chronic_diseases.length > 0 && `(${card.chronic_diseases.length})`}
        </h3>
        {!card.chronic_diseases.length ? (
          <p className="text-sm text-gray-400">Хронічних захворювань не зазначено</p>
        ) : (
          <div className="space-y-2">
            {card.chronic_diseases.map(d => (
              <div key={d.id} className="flex items-center gap-3 p-3 rounded-lg border border-gray-100">
                <span className="badge bg-blue-100 text-blue-700 font-mono shrink-0">
                  {d.icd10.code}
                </span>
                <span className="text-sm text-gray-700">{d.icd10.name_ua}</span>
                {d.diagnosed_at && (
                  <span className="ml-auto text-xs text-gray-400">
                    з {new Date(d.diagnosed_at).toLocaleDateString('uk-UA')}
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {card.notes && (
        <div className="card p-5">
          <h3 className="font-semibold text-gray-900 mb-2">Нотатки лікаря</h3>
          <p className="text-sm text-gray-700">{card.notes}</p>
        </div>
      )}
    </div>
  )
}
