import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { format } from 'date-fns'
import { ArrowLeft, Stethoscope, Upload, AlertTriangle, Plus, Edit2, Search, X, ExternalLink } from 'lucide-react'
import { patientsApi } from '../../api/patients'
import { encountersApi } from '../../api/encounters'
import { prescriptionsApi } from '../../api/prescriptions'
import { StatusBadge } from '../../components/shared/StatusBadge'
import { PageLoading } from '../../components/shared/LoadingSpinner'
import { EmptyState } from '../../components/shared/EmptyState'
import { toast } from '../../components/shared/Toast'
import type {
  BloodType, SmokingStatus, AlcoholStatus, AllergySeverity, DiagnosisType, ICD10SearchResponse,
} from '../../api/types'

const TABS = ['ЕМК', 'Прийоми', 'Рецепти', 'Направлення', 'Документи'] as const
type Tab = typeof TABS[number]

const SEVERITY_COLORS = {
  MILD: 'bg-yellow-100 text-yellow-700',
  MODERATE: 'bg-orange-100 text-orange-700',
  SEVERE: 'bg-red-100 text-red-700',
}
const SEVERITY_LABELS = { MILD: 'Легка', MODERATE: 'Помірна', SEVERE: 'Важка' }

const BLOOD_TYPES: BloodType[] = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-', 'UNKNOWN']
const SMOKING_OPTIONS: { value: SmokingStatus; label: string }[] = [
  { value: 'NEVER', label: 'Не курить' },
  { value: 'FORMER', label: 'Колишній курець' },
  { value: 'CURRENT', label: 'Курить' },
  { value: 'UNKNOWN', label: 'Невідомо' },
]
const ALCOHOL_OPTIONS: { value: AlcoholStatus; label: string }[] = [
  { value: 'NEVER', label: 'Не вживає' },
  { value: 'FORMER', label: 'Колишній вживач' },
  { value: 'CURRENT', label: 'Вживає' },
  { value: 'UNKNOWN', label: 'Невідомо' },
]
const SEVERITY_OPTIONS: { value: AllergySeverity; label: string }[] = [
  { value: 'MILD', label: 'Легка' },
  { value: 'MODERATE', label: 'Помірна' },
  { value: 'SEVERE', label: 'Важка' },
]
const DIAGNOSIS_TYPES: { value: DiagnosisType; label: string }[] = [
  { value: 'MAIN', label: 'Основний' },
  { value: 'COMPLICATION', label: 'Ускладнення' },
  { value: 'CONCOMITANT', label: 'Супутній' },
]

function calcBMI(height?: number, weight?: number): string {
  if (!height || !weight) return '—'
  const bmi = weight / ((height / 100) ** 2)
  return bmi.toFixed(1)
}

export function PatientDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [tab, setTab] = useState<Tab>('ЕМК')

  // EMK editing states
  const [editingCard, setEditingCard] = useState(false)
  const [cardForm, setCardForm] = useState<{
    blood_type: BloodType | ''
    height_cm: string
    weight_kg: string
    smoking_status: SmokingStatus | ''
    alcohol_status: AlcoholStatus | ''
    disability_group: string
    notes: string
  }>({ blood_type: '', height_cm: '', weight_kg: '', smoking_status: '', alcohol_status: '', disability_group: '', notes: '' })

  // Add allergy modal
  const [showAllergyForm, setShowAllergyForm] = useState(false)
  const [allergyForm, setAllergyForm] = useState({ substance: '', severity: 'MILD' as AllergySeverity, reaction: '' })

  // Add chronic disease modal
  const [showDiseaseForm, setShowDiseaseForm] = useState(false)
  const [diseaseQuery, setDiseaseQuery] = useState('')
  const [diseaseResults, setDiseaseResults] = useState<ICD10SearchResponse[]>([])
  const [diseaseForm, setDiseaseForm] = useState({ icd10_id: '', icd10_label: '', diagnosed_at: '', notes: '' })

  const { data: patient, isLoading } = useQuery({
    queryKey: ['patient', id],
    queryFn: () => patientsApi.get(id!).then(r => r.data),
    enabled: !!id,
  })

  const { data: medCard, refetch: refetchCard } = useQuery({
    queryKey: ['medical-card', id],
    queryFn: () => patientsApi.getMedicalCard(id!).then(r => r.data),
    enabled: !!id && tab === 'ЕМК',
  })

  const { data: encounters } = useQuery({
    queryKey: ['encounters', id],
    queryFn: () => encountersApi.getByPatient(id!).then(r => r.data),
    enabled: !!id && tab === 'Прийоми',
  })

  const { data: prescriptions } = useQuery({
    queryKey: ['prescriptions', id],
    queryFn: () => prescriptionsApi.getByPatient(id!).then(r => r.data),
    enabled: !!id && tab === 'Рецепти',
  })

  const { data: referrals } = useQuery({
    queryKey: ['referrals', id],
    queryFn: () => encountersApi.getReferralsByPatient(id!).then(r => r.data),
    enabled: !!id && tab === 'Направлення',
  })

  // Add referral form
  const [showReferralForm, setShowReferralForm] = useState(false)
  const [referralForm, setReferralForm] = useState({ encounter_id: '', reason: '' })
  const { data: patientEncounters } = useQuery({
    queryKey: ['encounters-for-referral', id],
    queryFn: () => encountersApi.getByPatient(id!).then(r => r.data),
    enabled: !!id && showReferralForm,
  })

  const addReferralMutation = useMutation({
    mutationFn: () => encountersApi.createReferral(referralForm.encounter_id, {
      reason: referralForm.reason || undefined,
    }),
    onSuccess: () => {
      toast('success', 'Направлення створено та відправлено до ЕСОЗ')
      setShowReferralForm(false)
      setReferralForm({ encounter_id: '', reason: '' })
      qc.invalidateQueries({ queryKey: ['referrals', id] })
    },
    onError: () => toast('error', 'Помилка створення направлення'),
  })

  const uploadMutation = useMutation({
    mutationFn: (file: File) => patientsApi.uploadDocument(id!, file),
    onSuccess: () => {
      toast('success', 'Документ завантажено')
      qc.invalidateQueries({ queryKey: ['patient', id] })
    },
    onError: () => toast('error', 'Помилка завантаження'),
  })

  const updateCardMutation = useMutation({
    mutationFn: () => patientsApi.updateMedicalCard(id!, {
      blood_type: cardForm.blood_type as BloodType || undefined,
      height_cm: cardForm.height_cm ? parseInt(cardForm.height_cm) : undefined,
      weight_kg: cardForm.weight_kg ? parseFloat(cardForm.weight_kg) : undefined,
      smoking_status: cardForm.smoking_status as SmokingStatus || undefined,
      alcohol_status: cardForm.alcohol_status as AlcoholStatus || undefined,
      disability_group: cardForm.disability_group || undefined,
      notes: cardForm.notes || undefined,
    }),
    onSuccess: () => {
      toast('success', 'Медичну картку оновлено')
      setEditingCard(false)
      refetchCard()
    },
    onError: () => toast('error', 'Помилка оновлення картки'),
  })

  const addAllergyMutation = useMutation({
    mutationFn: () => patientsApi.addAllergy(id!, {
      substance: allergyForm.substance,
      severity: allergyForm.severity,
      reaction: allergyForm.reaction || undefined,
    }),
    onSuccess: () => {
      toast('success', 'Алергію додано')
      setShowAllergyForm(false)
      setAllergyForm({ substance: '', severity: 'MILD', reaction: '' })
      refetchCard()
    },
    onError: () => toast('error', 'Помилка додавання алергії'),
  })

  const addDiseaseMutation = useMutation({
    mutationFn: () => patientsApi.addChronicDisease(id!, {
      icd10_id: diseaseForm.icd10_id,
      diagnosed_at: diseaseForm.diagnosed_at || undefined,
      notes: diseaseForm.notes || undefined,
    }),
    onSuccess: () => {
      toast('success', 'Хворобу додано')
      setShowDiseaseForm(false)
      setDiseaseForm({ icd10_id: '', icd10_label: '', diagnosed_at: '', notes: '' })
      setDiseaseQuery('')
      setDiseaseResults([])
      refetchCard()
    },
    onError: () => toast('error', 'Помилка додавання захворювання'),
  })

  function openEditCard() {
    setCardForm({
      blood_type: medCard?.blood_type ?? '',
      height_cm: medCard?.height_cm?.toString() ?? '',
      weight_kg: medCard?.weight_kg?.toString() ?? '',
      smoking_status: medCard?.smoking_status ?? '',
      alcohol_status: medCard?.alcohol_status ?? '',
      disability_group: medCard?.disability_group ?? '',
      notes: medCard?.notes ?? '',
    })
    setEditingCard(true)
  }

  async function searchICD10(q: string) {
    setDiseaseQuery(q)
    if (q.length < 2) { setDiseaseResults([]); return }
    try {
      const r = await encountersApi.searchICD10(q)
      setDiseaseResults(r.data)
    } catch { /* ignore */ }
  }

  if (isLoading) return <PageLoading />
  if (!patient) return <div className="text-gray-500">Пацієнта не знайдено</div>

  const fullName = `${patient.last_name} ${patient.first_name} ${patient.middle_name ?? ''}`
  const age = Math.floor((Date.now() - new Date(patient.birth_date).getTime()) / (365.25 * 24 * 3600 * 1000))

  return (
    <div>
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate(-1)} className="btn-secondary btn-sm btn">
          <ArrowLeft className="h-4 w-4" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{fullName}</h1>
          <p className="text-sm text-gray-500">
            {age} р. • ІПН: {patient.tax_id} • {patient.phone ?? 'Тел. не вказано'}
          </p>
        </div>
        <div className="ml-auto">
          <button
            onClick={() => navigate(`/doctor/encounters/new?patient_id=${id}`)}
            className="btn-primary btn"
          >
            <Stethoscope className="h-4 w-4" />
            Новий прийом
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200 mb-6">
        {TABS.map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors
              ${tab === t
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'}`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* ─── ЕМК TAB ─────────────────────────────────────────────────────── */}
      {tab === 'ЕМК' && (
        <div className="grid gap-4">
          {/* Vital info */}
          <div className="card p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-900">Основні показники</h3>
              {!editingCard && (
                <button onClick={openEditCard} className="btn-secondary btn-sm btn">
                  <Edit2 className="h-3.5 w-3.5" />
                  Редагувати
                </button>
              )}
            </div>

            {editingCard ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div>
                    <label className="label">Група крові</label>
                    <select className="input" value={cardForm.blood_type}
                      onChange={e => setCardForm(f => ({ ...f, blood_type: e.target.value as BloodType }))}>
                      <option value="">— не вказано —</option>
                      {BLOOD_TYPES.map(bt => <option key={bt} value={bt}>{bt}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="label">Зріст (см)</label>
                    <input type="number" className="input" placeholder="170" value={cardForm.height_cm}
                      onChange={e => setCardForm(f => ({ ...f, height_cm: e.target.value }))} />
                  </div>
                  <div>
                    <label className="label">Вага (кг)</label>
                    <input type="number" step="0.1" className="input" placeholder="70.0" value={cardForm.weight_kg}
                      onChange={e => setCardForm(f => ({ ...f, weight_kg: e.target.value }))} />
                  </div>
                  <div>
                    <label className="label">Тютюнопаління</label>
                    <select className="input" value={cardForm.smoking_status}
                      onChange={e => setCardForm(f => ({ ...f, smoking_status: e.target.value as SmokingStatus }))}>
                      <option value="">— не вказано —</option>
                      {SMOKING_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="label">Алкоголь</label>
                    <select className="input" value={cardForm.alcohol_status}
                      onChange={e => setCardForm(f => ({ ...f, alcohol_status: e.target.value as AlcoholStatus }))}>
                      <option value="">— не вказано —</option>
                      {ALCOHOL_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="label">Група інвалідності</label>
                    <input type="text" className="input" placeholder="I, II, III або немає"
                      value={cardForm.disability_group}
                      onChange={e => setCardForm(f => ({ ...f, disability_group: e.target.value }))} />
                  </div>
                </div>
                <div>
                  <label className="label">Нотатки</label>
                  <textarea rows={3} className="input resize-none" placeholder="Додаткові відомості…"
                    value={cardForm.notes}
                    onChange={e => setCardForm(f => ({ ...f, notes: e.target.value }))} />
                </div>
                <div className="flex gap-2">
                  <button onClick={() => updateCardMutation.mutate()} disabled={updateCardMutation.isPending}
                    className="btn-primary btn-sm btn">
                    Зберегти
                  </button>
                  <button onClick={() => setEditingCard(false)} className="btn-secondary btn-sm btn">
                    Скасувати
                  </button>
                </div>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  {[
                    ['Група крові', medCard?.blood_type ?? '—'],
                    ['Зріст', medCard?.height_cm ? `${medCard.height_cm} см` : '—'],
                    ['Вага', medCard?.weight_kg ? `${medCard.weight_kg} кг` : '—'],
                    ['ІМТ', calcBMI(medCard?.height_cm, medCard?.weight_kg)],
                    ['Тютюнопаління', SMOKING_OPTIONS.find(o => o.value === medCard?.smoking_status)?.label ?? '—'],
                    ['Алкоголь', ALCOHOL_OPTIONS.find(o => o.value === medCard?.alcohol_status)?.label ?? '—'],
                    ['Група інвалідності', medCard?.disability_group || '—'],
                  ].map(([label, val]) => (
                    <div key={label}>
                      <p className="text-gray-500 mb-1">{label}</p>
                      <p className="font-medium text-gray-900">{val}</p>
                    </div>
                  ))}
                </div>
                {medCard?.notes && (
                  <div className="mt-4 p-3 bg-gray-50 rounded-lg text-sm text-gray-700">
                    {medCard.notes}
                  </div>
                )}
              </>
            )}
          </div>

          {/* Allergies */}
          <div className="card p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-gray-900">Алергії</h3>
              <button onClick={() => setShowAllergyForm(v => !v)} className="btn-secondary btn-sm btn">
                <Plus className="h-3.5 w-3.5" />
                Додати
              </button>
            </div>

            {showAllergyForm && (
              <div className="mb-4 p-4 bg-orange-50 rounded-lg border border-orange-100 space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="label">Речовина / алерген</label>
                    <input type="text" className="input" placeholder="Пеніцилін, пилок, горіхи…"
                      value={allergyForm.substance}
                      onChange={e => setAllergyForm(f => ({ ...f, substance: e.target.value }))} />
                  </div>
                  <div>
                    <label className="label">Ступінь тяжкості</label>
                    <select className="input" value={allergyForm.severity}
                      onChange={e => setAllergyForm(f => ({ ...f, severity: e.target.value as AllergySeverity }))}>
                      {SEVERITY_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                    </select>
                  </div>
                </div>
                <div>
                  <label className="label">Реакція (необов'язково)</label>
                  <input type="text" className="input" placeholder="Висип, набряк, анафілаксія…"
                    value={allergyForm.reaction}
                    onChange={e => setAllergyForm(f => ({ ...f, reaction: e.target.value }))} />
                </div>
                <div className="flex gap-2">
                  <button onClick={() => addAllergyMutation.mutate()}
                    disabled={!allergyForm.substance || addAllergyMutation.isPending}
                    className="btn-primary btn-sm btn">
                    Зберегти
                  </button>
                  <button onClick={() => setShowAllergyForm(false)} className="btn-secondary btn-sm btn">
                    Скасувати
                  </button>
                </div>
              </div>
            )}

            {!medCard?.allergies?.length ? (
              <p className="text-sm text-gray-400">Алергій не зазначено</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {medCard.allergies.map(a => (
                  <div key={a.id} className="flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-1.5">
                    <AlertTriangle className="h-3.5 w-3.5 text-orange-500" />
                    <span className="text-sm font-medium">{a.substance}</span>
                    <span className={`badge text-xs ${SEVERITY_COLORS[a.severity]}`}>
                      {SEVERITY_LABELS[a.severity]}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Chronic diseases */}
          <div className="card p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-gray-900">Хронічні захворювання</h3>
              <button onClick={() => setShowDiseaseForm(v => !v)} className="btn-secondary btn-sm btn">
                <Plus className="h-3.5 w-3.5" />
                Додати
              </button>
            </div>

            {showDiseaseForm && (
              <div className="mb-4 p-4 bg-blue-50 rounded-lg border border-blue-100 space-y-3">
                <div>
                  <label className="label">Пошук МКБ-10</label>
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                    <input type="text" className="input pl-9"
                      placeholder="Введіть назву або код…"
                      value={diseaseQuery}
                      onChange={e => searchICD10(e.target.value)} />
                    {diseaseResults.length > 0 && (
                      <div className="absolute top-full left-0 right-0 z-10 mt-1 bg-white rounded-lg border border-gray-200 shadow-lg max-h-48 overflow-y-auto">
                        {diseaseResults.map(item => (
                          <button key={item.id}
                            className="w-full flex items-center gap-3 px-3 py-2 hover:bg-blue-50 text-left text-sm"
                            onClick={() => {
                              setDiseaseForm(f => ({ ...f, icd10_id: item.id, icd10_label: `${item.code} — ${item.name_ua}` }))
                              setDiseaseQuery(`${item.code} — ${item.name_ua}`)
                              setDiseaseResults([])
                            }}>
                            <span className="badge bg-blue-100 text-blue-700 font-mono shrink-0">{item.code}</span>
                            <span className="truncate text-gray-700">{item.name_ua}</span>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                  {diseaseForm.icd10_id && (
                    <div className="flex items-center gap-2 mt-2">
                      <span className="badge bg-blue-100 text-blue-700 text-xs">{diseaseForm.icd10_label}</span>
                      <button onClick={() => setDiseaseForm(f => ({ ...f, icd10_id: '', icd10_label: '' }))}>
                        <X className="h-3.5 w-3.5 text-gray-400" />
                      </button>
                    </div>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="label">Дата встановлення діагнозу</label>
                    <input type="date" className="input" value={diseaseForm.diagnosed_at}
                      onChange={e => setDiseaseForm(f => ({ ...f, diagnosed_at: e.target.value }))} />
                  </div>
                  <div>
                    <label className="label">Примітки</label>
                    <input type="text" className="input" placeholder="Стадія, форма…"
                      value={diseaseForm.notes}
                      onChange={e => setDiseaseForm(f => ({ ...f, notes: e.target.value }))} />
                  </div>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => addDiseaseMutation.mutate()}
                    disabled={!diseaseForm.icd10_id || addDiseaseMutation.isPending}
                    className="btn-primary btn-sm btn">
                    Зберегти
                  </button>
                  <button onClick={() => { setShowDiseaseForm(false); setDiseaseQuery(''); setDiseaseResults([]) }}
                    className="btn-secondary btn-sm btn">
                    Скасувати
                  </button>
                </div>
              </div>
            )}

            {!medCard?.chronic_diseases?.length ? (
              <p className="text-sm text-gray-400">Хронічних захворювань не зазначено</p>
            ) : (
              <div className="space-y-2">
                {medCard.chronic_diseases.map(d => (
                  <div key={d.id} className="flex items-center gap-3 text-sm">
                    <span className="badge bg-blue-100 text-blue-700 font-mono">
                      {d.icd10?.code}
                    </span>
                    <span className="text-gray-700">{d.icd10?.name_ua}</span>
                    {d.diagnosed_at && (
                      <span className="text-gray-400 text-xs ml-auto">
                        з {format(new Date(d.diagnosed_at), 'dd.MM.yyyy')}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ─── ПРИЙОМИ TAB ──────────────────────────────────────────────────── */}
      {tab === 'Прийоми' && (
        <div className="space-y-3">
          {!encounters?.length ? (
            <div className="card p-4"><EmptyState message="Прийомів не знайдено" /></div>
          ) : (
            encounters.map(enc => (
              <div key={enc.id} className="card p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <StatusBadge value={enc.status} />
                    <span className="text-sm text-gray-500">
                      {format(new Date(enc.started_at), 'dd.MM.yyyy HH:mm')}
                    </span>
                  </div>
                  {enc.pdf_url && (
                    <a href={enc.pdf_url} target="_blank" rel="noreferrer" className="btn-secondary btn-sm btn">
                      PDF
                    </a>
                  )}
                </div>
                {enc.complaints && (
                  <p className="text-sm text-gray-700">{enc.complaints}</p>
                )}
                {enc.diagnoses.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {enc.diagnoses.map(d => (
                      <span key={d.id} className="badge bg-gray-100 text-gray-600 font-mono text-xs">
                        {d.icd10?.code ?? d.icd10_id.slice(0, 8)}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {/* ─── РЕЦЕПТИ TAB ──────────────────────────────────────────────────── */}
      {tab === 'Рецепти' && (
        <div className="card overflow-hidden">
          {!prescriptions?.length ? (
            <EmptyState message="Рецептів не знайдено" />
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50">
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Препарат</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Дозування</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Статус</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Дата</th>
                </tr>
              </thead>
              <tbody>
                {prescriptions.map(rx => (
                  <tr key={rx.id} className="border-b border-gray-50">
                    <td className="px-4 py-3 font-medium">{rx.drug?.inn ?? '—'}</td>
                    <td className="px-4 py-3 text-gray-600">{rx.dosage} / {rx.frequency}</td>
                    <td className="px-4 py-3"><StatusBadge value={rx.status} /></td>
                    <td className="px-4 py-3 text-gray-500">
                      {format(new Date(rx.created_at), 'dd.MM.yyyy')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* ─── НАПРАВЛЕННЯ TAB ──────────────────────────────────────────────── */}
      {tab === 'Направлення' && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <button onClick={() => setShowReferralForm(v => !v)} className="btn-primary btn">
              <Plus className="h-4 w-4" />
              Нове направлення
            </button>
          </div>

          {showReferralForm && (
            <div className="card p-5 border-blue-200 bg-blue-50 space-y-4">
              <h3 className="font-semibold text-gray-900">Е-направлення до спеціаліста</h3>
              <div>
                <label className="label">Прийом (для прив'язки)</label>
                <select className="input" value={referralForm.encounter_id}
                  onChange={e => setReferralForm(f => ({ ...f, encounter_id: e.target.value }))}>
                  <option value="">— оберіть прийом —</option>
                  {patientEncounters?.map(enc => (
                    <option key={enc.id} value={enc.id}>
                      {format(new Date(enc.started_at), 'dd.MM.yyyy HH:mm')} — {enc.status}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label">Причина направлення</label>
                <textarea rows={3} className="input resize-none"
                  placeholder="Причина, скарги, мета консультації…"
                  value={referralForm.reason}
                  onChange={e => setReferralForm(f => ({ ...f, reason: e.target.value }))} />
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => addReferralMutation.mutate()}
                  disabled={!referralForm.encounter_id || addReferralMutation.isPending}
                  className="btn-primary btn-sm btn">
                  Відправити до ЕСОЗ
                </button>
                <button onClick={() => setShowReferralForm(false)} className="btn-secondary btn-sm btn">
                  Скасувати
                </button>
              </div>
            </div>
          )}

          {!referrals?.length ? (
            <div className="card p-4"><EmptyState message="Направлень не знайдено" /></div>
          ) : (
            <div className="space-y-3">
              {referrals.map(ref => (
                <div key={ref.id} className="card p-4">
                  <div className="flex items-center justify-between mb-2">
                    <StatusBadge value={ref.status} />
                    <span className="text-xs text-gray-400">
                      {format(new Date(ref.created_at), 'dd.MM.yyyy HH:mm')}
                    </span>
                  </div>
                  {ref.reason && <p className="text-sm text-gray-700 mb-2">{ref.reason}</p>}
                  {ref.esoz_referral_id && (
                    <div className="flex items-center gap-2 text-xs text-gray-500">
                      <ExternalLink className="h-3.5 w-3.5" />
                      ЕСОЗ ID: <span className="font-mono">{ref.esoz_referral_id}</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ─── ДОКУМЕНТИ TAB ────────────────────────────────────────────────── */}
      {tab === 'Документи' && (
        <div className="space-y-4">
          <div className="card p-4">
            <label className="flex items-center gap-3 cursor-pointer">
              <div className="btn-secondary btn">
                <Upload className="h-4 w-4" />
                Завантажити документ
              </div>
              <input
                type="file"
                className="hidden"
                accept=".pdf,.jpg,.jpeg,.png"
                onChange={e => {
                  const file = e.target.files?.[0]
                  if (file) uploadMutation.mutate(file)
                }}
              />
              <span className="text-sm text-gray-500">PDF, JPG, PNG до 10 МБ</span>
            </label>
          </div>
        </div>
      )}
    </div>
  )
}
