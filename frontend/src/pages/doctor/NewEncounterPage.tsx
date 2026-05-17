import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Save, CheckCircle, Plus, Search, AlertTriangle, User } from 'lucide-react'
import { encountersApi } from '../../api/encounters'
import { prescriptionsApi } from '../../api/prescriptions'
import { patientsApi } from '../../api/patients'
import { PageLoading } from '../../components/shared/LoadingSpinner'
import { toast } from '../../components/shared/Toast'
import type { ICD10SearchResponse, DrugResponse, DiagnosisType, PatientResponse } from '../../api/types'

const DIAGNOSIS_TYPES: { value: DiagnosisType; label: string }[] = [
  { value: 'MAIN', label: 'Основний' },
  { value: 'COMPLICATION', label: 'Ускладнення' },
  { value: 'CONCOMITANT', label: 'Супутній' },
]

// ─── Patient Picker (shown when no patient_id in URL) ─────────────────────────

function PatientPicker({ onSelect }: { onSelect: (p: PatientResponse) => void }) {
  const [search, setSearch] = useState('')
  const { data: patients, isLoading } = useQuery({
    queryKey: ['patients-search', search],
    queryFn: () => patientsApi.list({ search: search || undefined, limit: 20 }).then(r => r.data),
    enabled: true,
  })

  return (
    <div className="max-w-2xl">
      <h1 className="text-xl font-bold text-gray-900 mb-4">Оберіть пацієнта</h1>
      <div className="relative mb-4">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
        <input
          type="text"
          className="input pl-9"
          placeholder="Пошук за ПІБ, ІПН або телефоном…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          autoFocus
        />
      </div>
      {isLoading ? (
        <p className="text-sm text-gray-400">Завантаження…</p>
      ) : !patients?.length ? (
        <p className="text-sm text-gray-400">Пацієнтів не знайдено</p>
      ) : (
        <div className="space-y-2">
          {patients.map(p => {
            const age = Math.floor((Date.now() - new Date(p.birth_date).getTime()) / (365.25 * 24 * 3600 * 1000))
            return (
              <button
                key={p.id}
                onClick={() => onSelect(p)}
                className="w-full flex items-center gap-3 card p-3 hover:bg-blue-50 text-left transition-colors"
              >
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gray-100">
                  <User className="h-4 w-4 text-gray-500" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-900 truncate">
                    {p.last_name} {p.first_name} {p.middle_name ?? ''}
                  </p>
                  <p className="text-xs text-gray-500">
                    {age} р. • ІПН: {p.tax_id}{p.phone ? ` • ${p.phone}` : ''}
                  </p>
                </div>
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ─── Main encounter form ───────────────────────────────────────────────────────

export function NewEncounterPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const qc = useQueryClient()

  const [selectedPatient, setSelectedPatient] = useState<PatientResponse | null>(null)
  const patientIdParam = searchParams.get('patient_id') ?? ''
  const appointmentId = searchParams.get('appointment_id') ?? undefined
  const existingEncounterId = searchParams.get('encounter_id')
  const readOnlyParam = searchParams.get('readonly') === '1'
  const [isIcd10Focused, setIsIcd10Focused] = useState(false)
  const [isDrugFocused, setIsDrugFocused] = useState(false)

  const { data: existingEncounter } = useQuery({
    queryKey: ['encounter', existingEncounterId],
    queryFn: () => encountersApi.get(existingEncounterId!).then(r => r.data),
    enabled: !!existingEncounterId,
  })

  // If patient_id is in URL, load patient info
  const { data: urlPatient } = useQuery({
    queryKey: ['patient', patientIdParam || existingEncounter?.patient_id],
    queryFn: () => patientsApi.get((patientIdParam || existingEncounter?.patient_id)!).then(r => r.data),
    enabled: !!(patientIdParam || existingEncounter?.patient_id),
  })

  const activePatient = urlPatient ?? selectedPatient
  const patientId = patientIdParam || selectedPatient?.id || existingEncounter?.patient_id || ''
  const isReadOnly = readOnlyParam || (!!existingEncounter && existingEncounter.status !== 'IN_PROGRESS')

  const [encounterId, setEncounterId] = useState<string | null>(existingEncounterId)
  const [encounterStarted, setEncounterStarted] = useState(false)
  const encounterCreatingRef = useRef(false)
  const [form, setForm] = useState({
    complaints: '',
    anamnesis: '',
    objective_exam: '',
    treatment_plan: '',
    recommendations: '',
  })
  const [icd10Query, setIcd10Query] = useState('')
  const [icd10Results, setIcd10Results] = useState<ICD10SearchResponse[]>([])
  const [drugQuery, setDrugQuery] = useState('')
  const [drugResults, setDrugResults] = useState<DrugResponse[]>([])
  const [rxForm, setRxForm] = useState({
    drug_id: '',
    drug_name: '',
    dosage: '',
    frequency: '',
    duration_days: '',
    instructions: '',
  })
  const [allergyWarning, setAllergyWarning] = useState<string | null>(null)
  const [diagType, setDiagType] = useState<DiagnosisType>('MAIN')
  const autoSaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const { data: medCard } = useQuery({
    queryKey: ['medical-card', patientId],
    queryFn: () => patientsApi.getMedicalCard(patientId).then(r => r.data),
    enabled: !!patientId,
  })

  // Create encounter when patient is selected — ref guards against double-fire
  useEffect(() => {
    if (existingEncounterId) return
    if (!patientId || encounterCreatingRef.current || encounterStarted) return
    encounterCreatingRef.current = true
    setEncounterStarted(true)
    encountersApi.create({ patient_id: patientId, appointment_id: appointmentId })
      .then(r => setEncounterId(r.data.id))
      .catch((err) => {
        const detail = err?.response?.data?.detail
        const msg = typeof detail === 'string' ? detail : 'Помилка створення прийому'
        toast('error', msg)
        setEncounterStarted(false)
        encounterCreatingRef.current = false
      })
  }, [patientId, existingEncounterId])

  useEffect(() => {
    if (!existingEncounter) return
    setEncounterId(existingEncounter.id)
    setEncounterStarted(true)
    setForm({
      complaints: existingEncounter.complaints ?? '',
      anamnesis: existingEncounter.anamnesis ?? '',
      objective_exam: existingEncounter.objective_exam ?? '',
      treatment_plan: existingEncounter.treatment_plan ?? '',
      recommendations: existingEncounter.recommendations ?? '',
    })
  }, [existingEncounter])

  const save = useCallback(async () => {
    if (!encounterId || isReadOnly) return
    try {
      await encountersApi.update(encounterId, form)
    } catch { /* silent */ }
  }, [encounterId, form, isReadOnly])

  useEffect(() => {
    if (autoSaveTimer.current) clearTimeout(autoSaveTimer.current)
    autoSaveTimer.current = setTimeout(save, 30_000)
    return () => { if (autoSaveTimer.current) clearTimeout(autoSaveTimer.current) }
  }, [form, save])

  useEffect(() => {
    if (!isIcd10Focused || isReadOnly) { setIcd10Results([]); return }
    const t = setTimeout(() =>
      encountersApi.searchICD10(icd10Query).then(r => setIcd10Results(r.data)), 250)
    return () => clearTimeout(t)
  }, [icd10Query, isIcd10Focused, isReadOnly])

  useEffect(() => {
    if (!isDrugFocused || isReadOnly) { setDrugResults([]); return }
    const t = setTimeout(() =>
      prescriptionsApi.searchDrugs(drugQuery).then(r => setDrugResults(r.data)), 250)
    return () => clearTimeout(t)
  }, [drugQuery, isDrugFocused, isReadOnly])

  const addDiagnosisMutation = useMutation({
    mutationFn: (data: { icd10_id: string; type: DiagnosisType }) =>
      encountersApi.addDiagnosis(encounterId!, data),
    onSuccess: () => {
      toast('success', 'Діагноз додано')
      setIcd10Query('')
      setIcd10Results([])
      qc.invalidateQueries({ queryKey: ['encounter', encounterId] })
    },
    onError: () => toast('error', 'Помилка додавання діагнозу'),
  })

  const addRxMutation = useMutation({
    mutationFn: () =>
      prescriptionsApi.create({
        encounter_id: encounterId!,
        drug_id: rxForm.drug_id,
        dosage: rxForm.dosage || undefined,
        frequency: rxForm.frequency || undefined,
        duration_days: rxForm.duration_days ? parseInt(rxForm.duration_days) : undefined,
        instructions: rxForm.instructions || undefined,
      }),
    onSuccess: () => {
      toast('success', 'Рецепт виписано')
      setRxForm({ drug_id: '', drug_name: '', dosage: '', frequency: '', duration_days: '', instructions: '' })
      setDrugQuery('')
      setAllergyWarning(null)
    },
    onError: (err: any) => {
      const detail = err?.response?.data?.detail
      if (err?.response?.status === 409 && detail?.warning) {
        setAllergyWarning(
          `Увага: препарат "${detail.drug_inn}" конфліктує з алергією "${detail.allergy}" (${detail.severity})`
        )
      } else {
        toast('error', typeof detail === 'string' ? detail : 'Помилка виписки рецепту')
      }
    },
  })

  const completeMutation = useMutation({
    mutationFn: () => encountersApi.complete(encounterId!),
    onSuccess: () => {
      toast('success', 'Прийом завершено')
      navigate(patientId ? `/doctor/patients/${patientId}` : '/doctor')
    },
    onError: () => toast('error', 'Помилка завершення прийому'),
  })

  function selectDrug(drug: DrugResponse) {
    setRxForm(f => ({ ...f, drug_id: drug.id, drug_name: drug.inn }))
    setDrugQuery(drug.inn)
    setDrugResults([])
    const match = medCard?.allergies?.find(a =>
      a.substance.toLowerCase().includes(drug.inn.toLowerCase()) ||
      drug.inn.toLowerCase().includes(a.substance.toLowerCase())
    )
    if (match) {
      setAllergyWarning(`Увага: пацієнт має алергію на "${match.substance}" (${match.severity})`)
    } else {
      setAllergyWarning(null)
    }
  }

  // Show patient picker if no patient selected yet
  if (!patientId) {
    return (
      <div>
        <div className="flex items-center gap-4 mb-6">
          <button onClick={() => navigate(-1)} className="btn-secondary btn-sm btn">
            <ArrowLeft className="h-4 w-4" />
          </button>
          <h1 className="text-xl font-bold text-gray-900">Новий прийом</h1>
        </div>
        <PatientPicker onSelect={p => setSelectedPatient(p)} />
      </div>
    )
  }

  if (!encounterId) return <PageLoading />

  const fullName = activePatient
    ? `${activePatient.last_name} ${activePatient.first_name} ${activePatient.middle_name ?? ''}`
    : 'Завантаження…'

  return (
    <div className="max-w-3xl">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate(-1)} className="btn-secondary btn-sm btn">
          <ArrowLeft className="h-4 w-4" />
        </button>
        <div>
          <h1 className="text-xl font-bold text-gray-900">
            {isReadOnly ? 'Перегляд прийому' : 'Прийом'}
          </h1>
          <p className="text-sm text-gray-500">{fullName}</p>
          {existingEncounter && (
            <p className="text-xs text-gray-400 mt-1">Статус: {existingEncounter.status}</p>
          )}
        </div>
        <div className="ml-auto flex gap-2">
          {!isReadOnly && (
            <>
              <button onClick={save} className="btn-secondary btn-sm btn">
                <Save className="h-4 w-4" />
                Зберегти
              </button>
              <button
                onClick={() => completeMutation.mutate()}
                disabled={completeMutation.isPending}
                className="btn-primary btn-sm btn"
              >
                <CheckCircle className="h-4 w-4" />
                Завершити прийом
              </button>
            </>
          )}
        </div>
      </div>

      {/* Form fields */}
      <div className="space-y-4 mb-6">
        {([
          ['complaints', 'Скарги'],
          ['anamnesis', 'Анамнез захворювання'],
          ['objective_exam', 'Об\'єктивний огляд'],
          ['treatment_plan', 'План лікування'],
          ['recommendations', 'Рекомендації'],
        ] as [keyof typeof form, string][]).map(([key, label]) => (
          <div key={key} className="card p-4">
            <label className="label">{label}</label>
            <textarea
              rows={3}
              className="input resize-none"
              value={form[key]}
              disabled={isReadOnly}
              onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
              placeholder={`Введіть ${label.toLowerCase()}…`}
            />
          </div>
        ))}
      </div>

      {/* Diagnosis */}
      <div className="card p-5 mb-4">
        <h3 className="font-semibold text-gray-900 mb-3">Діагноз (МКБ-10)</h3>
        <div className="flex gap-2 mb-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              className="input pl-9"
              placeholder="Пошук МКБ-10…"
              value={icd10Query}
              disabled={isReadOnly}
              onFocus={() => setIsIcd10Focused(true)}
              onBlur={() => setTimeout(() => setIsIcd10Focused(false), 120)}
              onChange={e => setIcd10Query(e.target.value)}
            />
            {isIcd10Focused && icd10Results.length > 0 && (
              <div className="absolute top-full left-0 right-0 z-10 mt-1 bg-white rounded-lg border border-gray-200 shadow-lg max-h-48 overflow-y-auto">
                {icd10Results.map(item => (
                  <button
                    key={item.id}
                    className="w-full flex items-center gap-3 px-3 py-2 hover:bg-blue-50 text-left text-sm"
                    onClick={() => addDiagnosisMutation.mutate({ icd10_id: item.id, type: diagType })}
                    disabled={isReadOnly}
                  >
                    <span className="badge bg-blue-100 text-blue-700 font-mono shrink-0">{item.code}</span>
                    <div className="min-w-0">
                      <p className="truncate text-gray-800">{item.name_ua}</p>
                      {item.name_en && <p className="truncate text-xs text-gray-500">{item.name_en}</p>}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
          <select
            className="input w-40"
            value={diagType}
            disabled={isReadOnly}
            onChange={e => setDiagType(e.target.value as DiagnosisType)}
          >
            {DIAGNOSIS_TYPES.map(t => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Prescription */}
      <div className="card p-5">
        <h3 className="font-semibold text-gray-900 mb-3">Е-рецепт</h3>

        {allergyWarning && (
          <div className="flex items-center gap-2 p-3 bg-orange-50 border border-orange-200 rounded-lg mb-3 text-sm text-orange-700">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            {allergyWarning}
          </div>
        )}

        <div className="grid gap-3">
          <div className="relative">
            <label className="label">Препарат (МНН)</label>
            <input
              type="text"
              className="input"
              placeholder="Пошук препарату…"
              value={drugQuery}
              disabled={isReadOnly}
              onFocus={() => setIsDrugFocused(true)}
              onBlur={() => setTimeout(() => setIsDrugFocused(false), 120)}
              onChange={e => setDrugQuery(e.target.value)}
            />
            {isDrugFocused && drugResults.length > 0 && (
              <div className="absolute top-full left-0 right-0 z-10 mt-1 bg-white rounded-lg border border-gray-200 shadow-lg max-h-48 overflow-y-auto">
                {drugResults.map(drug => (
                  <button
                    key={drug.id}
                    className="w-full px-3 py-2 hover:bg-blue-50 text-left text-sm"
                    onClick={() => selectDrug(drug)}
                    disabled={isReadOnly}
                  >
                    <p className="font-medium text-gray-900">EN: {drug.inn}</p>
                    {drug.trade_name && <p className="text-gray-600">UA: {drug.trade_name}</p>}
                    <p className="text-xs text-gray-500">
                      {[drug.atc_code, drug.form, drug.dosage].filter(Boolean).join(' • ') || '—'}
                    </p>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Дозування</label>
              <input type="text" className="input" placeholder="500 мг" value={rxForm.dosage} disabled={isReadOnly}
                onChange={e => setRxForm(f => ({ ...f, dosage: e.target.value }))} />
            </div>
            <div>
              <label className="label">Частота прийому</label>
              <input type="text" className="input" placeholder="2 рази на день" value={rxForm.frequency} disabled={isReadOnly}
                onChange={e => setRxForm(f => ({ ...f, frequency: e.target.value }))} />
            </div>
            <div>
              <label className="label">Тривалість (днів)</label>
              <input type="number" className="input" placeholder="7" value={rxForm.duration_days} disabled={isReadOnly}
                onChange={e => setRxForm(f => ({ ...f, duration_days: e.target.value }))} />
            </div>
            <div>
              <label className="label">Інструкції</label>
              <input type="text" className="input" placeholder="Після їжі" value={rxForm.instructions} disabled={isReadOnly}
                onChange={e => setRxForm(f => ({ ...f, instructions: e.target.value }))} />
            </div>
          </div>

          <button
            onClick={() => addRxMutation.mutate()}
              disabled={isReadOnly || !rxForm.drug_id || addRxMutation.isPending}
            className="btn-secondary btn self-start"
          >
            <Plus className="h-4 w-4" />
            Виписати рецепт
          </button>
        </div>
      </div>
    </div>
  )
}
