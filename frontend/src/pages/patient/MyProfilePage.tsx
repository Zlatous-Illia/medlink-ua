import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { Camera, User } from 'lucide-react'
import { cabinetApi } from '../../api/patientCabinet'
import { useAuthStore } from '../../store/authStore'
import { PageLoading, LoadingSpinner } from '../../components/shared/LoadingSpinner'
import { toast } from '../../components/shared/Toast'

const profileSchema = z.object({
  first_name: z.string().min(1, 'Обов\'язково'),
  last_name: z.string().min(1, 'Обов\'язково'),
  middle_name: z.string().optional(),
  phone: z.string().optional(),
})
type ProfileData = z.infer<typeof profileSchema>

const pwSchema = z.object({
  current_password: z.string().min(1, 'Обов\'язково'),
  new_password: z.string().min(8, 'Мінімум 8 символів'),
  confirm: z.string(),
}).refine(d => d.new_password === d.confirm, {
  message: 'Паролі не збігаються', path: ['confirm'],
})
type PwData = z.infer<typeof pwSchema>

export function MyProfilePage() {
  const qc = useQueryClient()
  const { setUser } = useAuthStore()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const { data: profile, isLoading } = useQuery({
    queryKey: ['my-profile'],
    queryFn: () => cabinetApi.getProfile().then(r => r.data),
  })

  const profileForm = useForm<ProfileData>({ resolver: zodResolver(profileSchema) })
  const pwForm = useForm<PwData>({ resolver: zodResolver(pwSchema) })

  const profileMutation = useMutation({
    mutationFn: (data: ProfileData) => cabinetApi.updateProfile(data),
    onSuccess: r => {
      toast('success', 'Профіль оновлено')
      qc.invalidateQueries({ queryKey: ['my-profile'] })
      setUser({ ...r.data, is_active: true })
    },
    onError: () => toast('error', 'Помилка збереження'),
  })

  const avatarMutation = useMutation({
    mutationFn: (file: File) => cabinetApi.uploadAvatar(file),
    onSuccess: r => {
      toast('success', 'Аватар оновлено')
      qc.invalidateQueries({ queryKey: ['my-profile'] })
      setUser({ ...r.data, is_active: true })
    },
    onError: () => toast('error', 'Помилка завантаження аватара'),
  })

  const pwMutation = useMutation({
    mutationFn: (data: PwData) =>
      cabinetApi.changePassword(data.current_password, data.new_password),
    onSuccess: () => {
      toast('success', 'Пароль змінено')
      pwForm.reset()
    },
    onError: () => toast('error', 'Невірний поточний пароль'),
  })

  // Pre-fill form when profile loads
  useState(() => {
    if (profile) {
      profileForm.reset({
        first_name: profile.first_name,
        last_name: profile.last_name,
        middle_name: profile.middle_name ?? '',
        phone: profile.phone ?? '',
      })
    }
  })

  if (isLoading) return <PageLoading />

  const initials = profile
    ? `${profile.first_name[0]}${profile.last_name[0]}`.toUpperCase()
    : '?'

  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Мій профіль</h1>

      {/* Avatar */}
      <div className="card p-5 flex items-center gap-5">
        <div className="relative">
          {profile?.avatar_url ? (
            <img
              src={profile.avatar_url}
              alt="avatar"
              className="h-20 w-20 rounded-full object-cover"
            />
          ) : (
            <div className="flex h-20 w-20 items-center justify-center rounded-full bg-blue-100 text-2xl font-bold text-blue-700">
              {initials}
            </div>
          )}
          <button
            onClick={() => fileInputRef.current?.click()}
            className="absolute bottom-0 right-0 flex h-7 w-7 items-center justify-center rounded-full bg-blue-600 text-white shadow"
          >
            <Camera className="h-3.5 w-3.5" />
          </button>
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept="image/jpeg,image/png"
            onChange={e => {
              const f = e.target.files?.[0]
              if (f) avatarMutation.mutate(f)
            }}
          />
        </div>
        <div>
          <p className="font-semibold text-gray-900">
            {profile?.last_name} {profile?.first_name} {profile?.middle_name ?? ''}
          </p>
          <p className="text-sm text-gray-500">{profile?.email}</p>
        </div>
      </div>

      {/* Profile form */}
      <div className="card p-5">
        <h3 className="font-semibold text-gray-900 mb-4">Особисті дані</h3>
        <form onSubmit={profileForm.handleSubmit(d => profileMutation.mutate(d))} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Прізвище</label>
              <input type="text" className="input" {...profileForm.register('last_name')} />
            </div>
            <div>
              <label className="label">Ім'я</label>
              <input type="text" className="input" {...profileForm.register('first_name')} />
            </div>
            <div>
              <label className="label">По батькові</label>
              <input type="text" className="input" {...profileForm.register('middle_name')} />
            </div>
            <div>
              <label className="label">Телефон</label>
              <input type="tel" className="input" placeholder="+380…" {...profileForm.register('phone')} />
            </div>
          </div>
          <div>
            <label className="label">Email (не редагується)</label>
            <input type="email" className="input bg-gray-50" value={profile?.email ?? ''} disabled />
          </div>
          <div className="flex justify-end">
            <button type="submit" className="btn-primary btn" disabled={profileMutation.isPending}>
              {profileMutation.isPending ? <LoadingSpinner size="sm" /> : 'Зберегти'}
            </button>
          </div>
        </form>
      </div>

      {/* Change password */}
      <div className="card p-5">
        <h3 className="font-semibold text-gray-900 mb-4">Зміна пароля</h3>
        <form onSubmit={pwForm.handleSubmit(d => pwMutation.mutate(d))} className="space-y-4">
          <div>
            <label className="label">Поточний пароль</label>
            <input type="password" className="input" {...pwForm.register('current_password')} />
            {pwForm.formState.errors.current_password && (
              <p className="error-msg">{pwForm.formState.errors.current_password.message}</p>
            )}
          </div>
          <div>
            <label className="label">Новий пароль</label>
            <input type="password" className="input" {...pwForm.register('new_password')} />
            {pwForm.formState.errors.new_password && (
              <p className="error-msg">{pwForm.formState.errors.new_password.message}</p>
            )}
          </div>
          <div>
            <label className="label">Підтвердити пароль</label>
            <input type="password" className="input" {...pwForm.register('confirm')} />
            {pwForm.formState.errors.confirm && (
              <p className="error-msg">{pwForm.formState.errors.confirm.message}</p>
            )}
          </div>
          <div className="flex justify-end">
            <button type="submit" className="btn-primary btn" disabled={pwMutation.isPending}>
              {pwMutation.isPending ? <LoadingSpinner size="sm" /> : 'Змінити пароль'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
