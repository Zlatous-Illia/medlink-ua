import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { Stethoscope } from 'lucide-react'
import { authApi } from '../../api/auth'
import { LoadingSpinner } from '../../components/shared/LoadingSpinner'

const schema = z.object({
  email: z.string().email('Невірний формат email'),
  password: z
    .string()
    .min(8, 'Мінімум 8 символів')
    .regex(/[A-Z]/, 'Потрібна хоча б одна велика літера')
    .regex(/\d/, 'Потрібна хоча б одна цифра'),
  last_name: z.string().min(1, "Обов'язкове поле"),
  first_name: z.string().min(1, "Обов'язкове поле"),
  middle_name: z.string().optional(),
  phone: z.string().optional(),
  tax_id: z.string().max(10).optional(),
  birth_date: z.string().optional(),
  gender: z.enum(['MALE', 'FEMALE', 'OTHER', '']).optional(),
})
type FormData = z.infer<typeof schema>

export function RegisterPage() {
  const navigate = useNavigate()
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  async function onSubmit(data: FormData) {
    setError('')
    try {
      await authApi.register({
        ...data,
        role: 'PATIENT',
        gender: data.gender || undefined,
      })
      setSuccess(true)
      setTimeout(() => navigate('/login'), 2500)
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(msg || 'Помилка реєстрації')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <div className="card w-full max-w-lg p-8">
        <div className="flex flex-col items-center mb-8">
          <div className="flex items-center gap-2 mb-2">
            <Stethoscope className="h-8 w-8 text-blue-600" />
            <span className="text-2xl font-bold text-gray-900">MedLink UA</span>
          </div>
          <p className="text-sm text-gray-500">Електронна медична система</p>
        </div>

        <h1 className="text-xl font-semibold text-gray-900 mb-6">Реєстрація пацієнта</h1>

        {success && (
          <div className="mb-4 rounded-lg bg-green-50 border border-green-200 px-4 py-3 text-sm text-green-700">
            Реєстрацію успішно завершено! Перенаправлення на сторінку входу…
          </div>
        )}

        {error && (
          <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
          <div>
            <label className="label">Email *</label>
            <input type="email" className="input" placeholder="patient@example.ua" {...register('email')} />
            {errors.email && <p className="error-msg">{errors.email.message}</p>}
          </div>

          <div>
            <label className="label">Пароль *</label>
            <input type="password" className="input" placeholder="Мін. 8 символів, велика літера, цифра" {...register('password')} />
            {errors.password && <p className="error-msg">{errors.password.message}</p>}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Прізвище *</label>
              <input className="input" {...register('last_name')} />
              {errors.last_name && <p className="error-msg">{errors.last_name.message}</p>}
            </div>
            <div>
              <label className="label">Ім'я *</label>
              <input className="input" {...register('first_name')} />
              {errors.first_name && <p className="error-msg">{errors.first_name.message}</p>}
            </div>
          </div>

          <div>
            <label className="label">По батькові</label>
            <input className="input" {...register('middle_name')} />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Телефон</label>
              <input className="input" placeholder="+380XXXXXXXXX" {...register('phone')} />
            </div>
            <div>
              <label className="label">РНОКПП (ІПН)</label>
              <input className="input" maxLength={10} {...register('tax_id')} />
            </div>
            <div>
              <label className="label">Дата народження</label>
              <input type="date" className="input" {...register('birth_date')} />
            </div>
            <div>
              <label className="label">Стать</label>
              <select className="input" {...register('gender')}>
                <option value="">Не вказано</option>
                <option value="MALE">Чоловіча</option>
                <option value="FEMALE">Жіноча</option>
                <option value="OTHER">Інша</option>
              </select>
            </div>
          </div>

          <button
            type="submit"
            className="btn-primary w-full mt-2"
            disabled={isSubmitting || success}
          >
            {isSubmitting ? <LoadingSpinner size="sm" /> : 'Зареєструватись'}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-gray-600">
          Вже маєте аккаунт?{' '}
          <Link to="/login" className="text-blue-600 hover:underline font-medium">
            Увійти
          </Link>
        </p>
      </div>
    </div>
  )
}