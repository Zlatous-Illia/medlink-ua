import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { ArrowLeft } from 'lucide-react'
import { patientsApi } from '../../api/patients'
import { LoadingSpinner } from '../../components/shared/LoadingSpinner'
import { toast } from '../../components/shared/Toast'

const schema = z.object({
  tax_id: z.string().length(10, 'ІПН — 10 цифр'),
  first_name: z.string().min(1, 'Обов\'язково'),
  last_name: z.string().min(1, 'Обов\'язково'),
  middle_name: z.string().optional(),
  birth_date: z.string().min(1, 'Обов\'язково'),
  gender: z.enum(['MALE', 'FEMALE', 'OTHER']),
  phone: z.string().optional(),
  email: z.string().email('Невірний email').optional().or(z.literal('')),
  city: z.string().optional(),
  street: z.string().optional(),
})
type FormData = z.infer<typeof schema>

export function RegisterPatientPage() {
  const navigate = useNavigate()
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { gender: 'MALE' },
  })

  async function onSubmit(data: FormData) {
    try {
      const { city, street, email, ...rest } = data
      const res = await patientsApi.create({
        ...rest,
        email: email || undefined,
        address: city || street
          ? { ...(city ? { city } : {}), ...(street ? { street } : {}) }
          : undefined,
      })
      toast('success', 'Пацієнта зареєстровано')
      navigate(`/doctor/patients/${res.data.id}`)
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast('error', msg || 'Помилка реєстрації')
    }
  }

  return (
    <div className="max-w-2xl">
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate(-1)} className="btn-secondary btn-sm btn">
          <ArrowLeft className="h-4 w-4" />
        </button>
        <h1 className="text-2xl font-bold text-gray-900">Реєстрація пацієнта</h1>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="card p-5">
          <h3 className="font-semibold text-gray-900 mb-4">Персональні дані</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="label">ІПН (РНОКПП) *</label>
              <input type="text" className="input font-mono" placeholder="1234567890" {...register('tax_id')} />
              {errors.tax_id && <p className="error-msg">{errors.tax_id.message}</p>}
            </div>
            <div>
              <label className="label">Стать *</label>
              <select className="input" {...register('gender')}>
                <option value="MALE">Чоловіча</option>
                <option value="FEMALE">Жіноча</option>
                <option value="OTHER">Інше</option>
              </select>
            </div>
            <div>
              <label className="label">Прізвище *</label>
              <input type="text" className="input" {...register('last_name')} />
              {errors.last_name && <p className="error-msg">{errors.last_name.message}</p>}
            </div>
            <div>
              <label className="label">Ім'я *</label>
              <input type="text" className="input" {...register('first_name')} />
              {errors.first_name && <p className="error-msg">{errors.first_name.message}</p>}
            </div>
            <div>
              <label className="label">По батькові</label>
              <input type="text" className="input" {...register('middle_name')} />
            </div>
            <div>
              <label className="label">Дата народження *</label>
              <input type="date" className="input" {...register('birth_date')} />
              {errors.birth_date && <p className="error-msg">{errors.birth_date.message}</p>}
            </div>
            <div>
              <label className="label">Телефон</label>
              <input type="tel" className="input" placeholder="+380991234567" {...register('phone')} />
            </div>
            <div>
              <label className="label">Email</label>
              <input type="email" className="input" {...register('email')} />
              {errors.email && <p className="error-msg">{errors.email.message}</p>}
            </div>
          </div>
        </div>

        <div className="card p-5">
          <h3 className="font-semibold text-gray-900 mb-4">Адреса</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="label">Місто</label>
              <input type="text" className="input" placeholder="Київ" {...register('city')} />
            </div>
            <div>
              <label className="label">Вулиця, будинок</label>
              <input type="text" className="input" placeholder="вул. Хрещатик, 1" {...register('street')} />
            </div>
          </div>
        </div>

        <div className="flex gap-3 justify-end">
          <button type="button" onClick={() => navigate(-1)} className="btn-secondary btn">
            Скасувати
          </button>
          <button type="submit" className="btn-primary btn" disabled={isSubmitting}>
            {isSubmitting ? <LoadingSpinner size="sm" /> : 'Зареєструвати'}
          </button>
        </div>
      </form>
    </div>
  )
}
