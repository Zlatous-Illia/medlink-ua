import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { Stethoscope, CheckCircle } from 'lucide-react'
import { authApi } from '../../api/auth'
import { LoadingSpinner } from '../../components/shared/LoadingSpinner'

const schema = z.object({ email: z.string().email('Невірний email') })
type FormData = z.infer<typeof schema>

export function ForgotPasswordPage() {
  const [sent, setSent] = useState(false)
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  async function onSubmit(data: FormData) {
    await authApi.forgotPassword(data.email)
    setSent(true)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <div className="card w-full max-w-sm p-8">
        <div className="flex items-center gap-2 mb-6">
          <Stethoscope className="h-6 w-6 text-blue-600" />
          <span className="text-lg font-bold text-gray-900">MedLink UA</span>
        </div>

        {sent ? (
          <div className="text-center py-4">
            <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-3" />
            <h2 className="text-lg font-semibold text-gray-900 mb-2">Запит надіслано</h2>
            <p className="text-sm text-gray-500 mb-4">
              Токен скидання пароля виведено в консоль сервера (DEV режим).
            </p>
            <Link to="/reset-password" className="btn-primary btn">
              Ввести токен
            </Link>
          </div>
        ) : (
          <>
            <h1 className="text-xl font-semibold text-gray-900 mb-2">Скидання пароля</h1>
            <p className="text-sm text-gray-500 mb-6">
              Введіть email — ми надішлемо токен для скидання пароля.
            </p>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div>
                <label className="label">Email</label>
                <input type="email" className="input" {...register('email')} />
                {errors.email && <p className="error-msg">{errors.email.message}</p>}
              </div>
              <button type="submit" className="btn-primary w-full" disabled={isSubmitting}>
                {isSubmitting ? <LoadingSpinner size="sm" /> : 'Надіслати'}
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
