import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { format, addDays } from 'date-fns'
import { ArrowLeft, ChevronLeft, ChevronRight, User } from 'lucide-react'
import { appointmentsApi } from '../../api/appointments'
import { PageLoading, LoadingSpinner } from '../../components/shared/LoadingSpinner'
import { toast } from '../../components/shared/Toast'
import type { DoctorListResponse } from '../../api/types'

export function BookAppointmentPage() {
  const navigate = useNavigate()
  const [step, setStep] = useState<1 | 2 | 3>(1)
  const [doctor, setDoctor] = useState<DoctorListResponse | null>(null)
  const [selectedDate, setSelectedDate] = useState(format(new Date(), 'yyyy-MM-dd'))
  const [selectedSlot, setSelectedSlot] = useState<string | null>(null)
  const [reason, setReason] = useState('')

  const { data: doctors, isLoading: drLoading } = useQuery({
    queryKey: ['doctors'],
    queryFn: () => appointmentsApi.listDoctors().then(r => r.data),
  })

  const { data: slots, isLoading: slotsLoading } = useQuery({
    queryKey: ['slots', doctor?.id, selectedDate],
    queryFn: () => appointmentsApi.getSlots(doctor!.id, selectedDate).then(r => r.data),
    enabled: !!doctor && step === 2,
  })

  const bookMutation = useMutation({
    mutationFn: () =>
      appointmentsApi.create({
        doctor_id: doctor!.id,
        slot_datetime: selectedSlot!,
        reason: reason || undefined,
      }),
    onSuccess: () => {
      toast('success', 'Запис підтверджено!')
      navigate('/patient/appointments')
    },
    onError: () => toast('error', 'Не вдалося записатись. Можливо, цей час вже зайнятий.'),
  })

  function prevDay() { setSelectedDate(d => format(addDays(new Date(d), -1), 'yyyy-MM-dd')) }
  function nextDay() { setSelectedDate(d => format(addDays(new Date(d), 1), 'yyyy-MM-dd')) }

  const availableSlots = slots?.filter(s => s.is_available) ?? []

  return (
    <div className="max-w-2xl">
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => step > 1 ? setStep(s => (s - 1) as typeof step) : navigate(-1)} className="btn-secondary btn-sm btn">
          <ArrowLeft className="h-4 w-4" />
        </button>
        <h1 className="text-2xl font-bold text-gray-900">Запис до лікаря</h1>
      </div>

      {/* Steps indicator */}
      <div className="flex items-center gap-2 mb-8">
        {['Лікар', 'Час', 'Підтвердження'].map((label, i) => (
          <div key={label} className="flex items-center gap-2">
            <div className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold
              ${step > i + 1 ? 'bg-green-500 text-white' : step === i + 1 ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-400'}`}>
              {i + 1}
            </div>
            <span className={`text-sm ${step === i + 1 ? 'font-medium text-gray-900' : 'text-gray-400'}`}>{label}</span>
            {i < 2 && <div className="w-8 h-px bg-gray-200" />}
          </div>
        ))}
      </div>

      {/* Step 1: Doctor */}
      {step === 1 && (
        <div>
          {drLoading ? <PageLoading /> : (
            <div className="space-y-2">
              {doctors?.map(dr => (
                <div
                  key={dr.id}
                  onClick={() => { setDoctor(dr); setStep(2) }}
                  className="card p-4 flex items-center gap-4 cursor-pointer hover:border-blue-300 hover:bg-blue-50 transition-colors"
                >
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gray-100 shrink-0">
                    {dr.photo_url
                      ? <img src={dr.photo_url} alt="" className="h-12 w-12 rounded-full object-cover" />
                      : <User className="h-6 w-6 text-gray-500" />
                    }
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">{dr.full_name}</p>
                    {dr.specialization && (
                      <p className="text-sm text-gray-500">{dr.specialization.name_ua}</p>
                    )}
                    {dr.experience_years && (
                      <p className="text-xs text-gray-400">Досвід: {dr.experience_years} р.</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Step 2: Slot */}
      {step === 2 && doctor && (
        <div>
          <div className="card p-3 mb-4">
            <p className="text-sm font-medium text-gray-900">{doctor.full_name}</p>
            {doctor.specialization && <p className="text-xs text-gray-500">{doctor.specialization.name_ua}</p>}
          </div>

          {/* Date navigation */}
          <div className="flex items-center gap-3 mb-4">
            <button onClick={prevDay} className="btn-secondary btn-sm btn"><ChevronLeft className="h-4 w-4" /></button>
            <input
              type="date"
              className="input"
              value={selectedDate}
              min={format(new Date(), 'yyyy-MM-dd')}
              onChange={e => setSelectedDate(e.target.value)}
            />
            <button onClick={nextDay} className="btn-secondary btn-sm btn"><ChevronRight className="h-4 w-4" /></button>
          </div>

          {slotsLoading ? <PageLoading /> : !availableSlots.length ? (
            <div className="text-center py-8 text-gray-400 text-sm">
              На цей день немає вільних слотів
            </div>
          ) : (
            <div className="grid grid-cols-4 gap-2">
              {availableSlots.map(slot => (
                <button
                  key={slot.slot_datetime}
                  onClick={() => { setSelectedSlot(slot.slot_datetime); setStep(3) }}
                  className={`rounded-lg border py-2 text-sm font-medium transition-colors
                    ${selectedSlot === slot.slot_datetime
                      ? 'border-blue-600 bg-blue-600 text-white'
                      : 'border-gray-200 hover:border-blue-300 hover:bg-blue-50'}`}
                >
                  {format(new Date(slot.slot_datetime), 'HH:mm')}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Step 3: Confirm */}
      {step === 3 && doctor && selectedSlot && (
        <div className="card p-5 space-y-4">
          <h3 className="font-semibold text-gray-900">Підтвердження запису</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">Лікар:</span>
              <span className="font-medium">{doctor.full_name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Час:</span>
              <span className="font-medium">{format(new Date(selectedSlot), 'dd.MM.yyyy, HH:mm')}</span>
            </div>
          </div>
          <div>
            <label className="label">Причина звернення (необов'язково)</label>
            <input
              type="text"
              className="input"
              placeholder="Напр.: огляд, температура, головний біль…"
              value={reason}
              onChange={e => setReason(e.target.value)}
            />
          </div>
          <button
            onClick={() => bookMutation.mutate()}
            disabled={bookMutation.isPending}
            className="btn-primary w-full"
          >
            {bookMutation.isPending ? <LoadingSpinner size="sm" /> : 'Підтвердити запис'}
          </button>
        </div>
      )}
    </div>
  )
}
