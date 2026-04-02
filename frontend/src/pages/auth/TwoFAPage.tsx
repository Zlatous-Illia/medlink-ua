import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Stethoscope, Mail } from 'lucide-react'
import { authApi } from '../../api/auth'
import { useAuthStore } from '../../store/authStore'
import { LoadingSpinner } from '../../components/shared/LoadingSpinner'

export function TwoFAPage() {
  const navigate = useNavigate()
  const { pendingEmail, login, setTokens } = useAuthStore()
  const [digits, setDigits] = useState(['', '', '', '', '', ''])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const inputs = useRef<Array<HTMLInputElement | null>>([])

  useEffect(() => {
    if (!pendingEmail) navigate('/login', { replace: true })
    inputs.current[0]?.focus()
  }, [])

  function handleChange(idx: number, val: string) {
    if (!/^\d?$/.test(val)) return
    const next = [...digits]
    next[idx] = val
    setDigits(next)
    if (val && idx < 5) inputs.current[idx + 1]?.focus()
    if (next.every(d => d !== '')) submit(next.join(''))
  }

  function handleKeyDown(idx: number, e: React.KeyboardEvent) {
    if (e.key === 'Backspace' && !digits[idx] && idx > 0) {
      inputs.current[idx - 1]?.focus()
    }
  }

  function handlePaste(e: React.ClipboardEvent) {
    const text = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6)
    if (text.length === 6) {
      const next = text.split('')
      setDigits(next)
      submit(text)
    }
  }

  async function submit(code: string) {
    if (!pendingEmail) return
    setError('')
    setLoading(true)
    try {
      const { data } = await authApi.verify2FA(pendingEmail, code)
      setTokens(data.access_token, data.refresh_token)
      const { data: user } = await authApi.me()
      login(
        {
          id: user.id,
          email: user.email,
          first_name: user.first_name,
          last_name: user.last_name,
          middle_name: user.middle_name,
          role: user.role,
          avatar_url: user.avatar_url,
          is_active: user.is_active,
        },
        data.access_token,
        data.refresh_token
      )
      navigate('/')
    } catch {
      setError('Невірний або прострочений код. Перевірте термінал сервера.')
      setDigits(['', '', '', '', '', ''])
      inputs.current[0]?.focus()
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <div className="card w-full max-w-sm p-8">
        <div className="flex flex-col items-center mb-8">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-100 mb-3">
            <Mail className="h-6 w-6 text-blue-600" />
          </div>
          <h1 className="text-xl font-semibold text-gray-900">Двофакторна аутентифікація</h1>
          <p className="text-sm text-gray-500 mt-1 text-center">
            Введіть 6-значний код з консолі сервера
            {pendingEmail && <><br /><span className="font-medium text-gray-700">{pendingEmail}</span></>}
          </p>
        </div>

        {error && (
          <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700 text-center">
            {error}
          </div>
        )}

        <div className="flex gap-2 justify-center mb-6" onPaste={handlePaste}>
          {digits.map((d, i) => (
            <input
              key={i}
              ref={el => { inputs.current[i] = el }}
              type="text"
              inputMode="numeric"
              maxLength={1}
              value={d}
              onChange={e => handleChange(i, e.target.value)}
              onKeyDown={e => handleKeyDown(i, e)}
              className="h-12 w-10 rounded-lg border border-gray-300 text-center text-xl font-bold
                focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          ))}
        </div>

        {loading && (
          <div className="flex justify-center">
            <LoadingSpinner />
          </div>
        )}

        <p className="text-center text-xs text-gray-400 mt-4">
          OTP-код виводиться в термінал бекенду (DEV режим)
        </p>

        <button
          onClick={() => navigate('/login')}
          className="mt-4 w-full text-center text-sm text-blue-600 hover:underline"
        >
          Повернутись до входу
        </button>
      </div>
    </div>
  )
}
