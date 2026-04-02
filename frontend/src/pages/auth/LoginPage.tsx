import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { Stethoscope, Eye, EyeOff } from 'lucide-react'
import { authApi } from '../../api/auth'
import { useAuthStore } from '../../store/authStore'
import { LoadingSpinner } from '../../components/shared/LoadingSpinner'

const schema = z.object({
  email: z.string().email('Невірний формат email'),
  password: z.string().min(1, 'Введіть пароль'),
})
type FormData = z.infer<typeof schema>

export function LoginPage() {
  const navigate = useNavigate()
  const setPendingEmail = useAuthStore(s => s.setPendingEmail)
  const [showPw, setShowPw] = useState(false)
  const [error, setError] = useState('')
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  async function onSubmit(data: FormData) {
    setError('')
    try {
      await authApi.login(data.email, data.password)
      setPendingEmail(data.email)
      navigate('/login/2fa')
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail
      setError(msg || 'Невірний email або пароль')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <div className="card w-full max-w-md p-8">
        {/* Header */}
        <div className="flex flex-col items-center mb-8">
          <div className="flex items-center gap-2 mb-2">
            <Stethoscope className="h-8 w-8 text-blue-600" />
            <span className="text-2xl font-bold text-gray-900">MedLink UA</span>
          </div>
          <p className="text-sm text-gray-500">Електронна медична система</p>
        </div>

        <h1 className="text-xl font-semibold text-gray-900 mb-6">Вхід до системи</h1>

        {error && (
          <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="label">Email</label>
            <input
              type="email"
              className="input"
              placeholder="doctor@clinic.ua"
              {...register('email')}
            />
            {errors.email && <p className="error-msg">{errors.email.message}</p>}
          </div>

          <div>
            <label className="label">Пароль</label>
            <div className="relative">
              <input
                type={showPw ? 'text' : 'password'}
                className="input pr-10"
                placeholder="••••••••"
                {...register('password')}
              />
              <button
                type="button"
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400"
                onClick={() => setShowPw(v => !v)}
              >
                {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            {errors.password && <p className="error-msg">{errors.password.message}</p>}
          </div>

          <div className="flex justify-end">
            <Link to="/forgot-password" className="text-sm text-blue-600 hover:underline">
              Забули пароль?
            </Link>
          </div>

          <button type="submit" className="btn-primary w-full" disabled={isSubmitting}>
            {isSubmitting ? <LoadingSpinner size="sm" /> : 'Увійти'}
          </button>
        </form>
      </div>
    </div>
  )
}
