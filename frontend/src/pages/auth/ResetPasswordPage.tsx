import { useState } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { Stethoscope, CheckCircle } from 'lucide-react'
import { authApi } from '../../api/auth'
import { LoadingSpinner } from '../../components/shared/LoadingSpinner'

const schema = z.object({
  token: z.string().min(1, 'Введіть токен'),
  new_password: z.string().min(8, 'Мінімум 8 символів'),
  confirm: z.string(),
}).refine(d => d.new_password === d.confirm, {
  message: 'Паролі не збігаються',
  path: ['confirm'],
})
type FormData = z.infer<typeof schema>

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [done, setDone] = useState(false)
  const [error, setError] = useState('')

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { token: searchParams.get('token') ?? '' },
  })

  async function onSubmit(data: FormData) {
    setError('')
    try {
      await authApi.resetPassword(data.token, data.new_password)
      setDone(true)
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(msg || 'Невірний або прострочений токен')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <div className="card w-full max-w-sm p-8">
        <div className="flex items-center gap-2 mb-6">
          <Stethoscope className="h-6 w-6 text-blue-600" />
          <span className="text-lg font-bold text-gray-900">MedLink UA</span>
        </div>

        {done ? (
          <div className="text-center py-4">
            <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-3" />
            <h2 className="text-lg font-semibold mb-2">Пароль змінено!</h2>
            <p className="text-sm text-gray-500 mb-4">Тепер ви можете увійти з новим паролем.</p>
            <button onClick={() => navigate('/login')} className="btn-primary btn">
              Увійти
            </button>
          </div>
        ) : (
          <>
            <h1 className="text-xl font-semibold mb-2">Новий пароль</h1>
            {error && (
              <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
                {error}
              </div>
            )}
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div>
                <label className="label">Токен з консолі сервера</label>
                <input type="text" className="input font-mono text-xs" {...register('token')} />
                {errors.token && <p className="error-msg">{errors.token.message}</p>}
              </div>
              <div>
                <label className="label">Новий пароль</label>
                <input type="password" className="input" {...register('new_password')} />
                {errors.new_password && <p className="error-msg">{errors.new_password.message}</p>}
              </div>
              <div>
                <label className="label">Підтвердити пароль</label>
                <input type="password" className="input" {...register('confirm')} />
                {errors.confirm && <p className="error-msg">{errors.confirm.message}</p>}
              </div>
              <button type="submit" className="btn-primary w-full" disabled={isSubmitting}>
                {isSubmitting ? <LoadingSpinner size="sm" /> : 'Змінити пароль'}
              </button>
            </form>
          </>
        )}

        <Link to="/login" className="block text-center text-sm text-blue-600 hover:underline mt-6">
          Повернутись до входу
        </Link>
      </div>
    </div>
  )
}
