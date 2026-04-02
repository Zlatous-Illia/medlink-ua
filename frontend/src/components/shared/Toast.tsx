import { create } from 'zustand'
import { useEffect } from 'react'
import { CheckCircle, XCircle, X } from 'lucide-react'

interface Toast {
  id: string
  type: 'success' | 'error'
  message: string
}

interface ToastStore {
  toasts: Toast[]
  add: (type: Toast['type'], message: string) => void
  remove: (id: string) => void
}

export const useToast = create<ToastStore>(set => ({
  toasts: [],
  add: (type, message) => {
    const id = Math.random().toString(36).slice(2)
    set(s => ({ toasts: [...s.toasts, { id, type, message }] }))
    setTimeout(() => set(s => ({ toasts: s.toasts.filter(t => t.id !== id) })), 4000)
  },
  remove: id => set(s => ({ toasts: s.toasts.filter(t => t.id !== id) })),
}))

export function toast(type: Toast['type'], message: string) {
  useToast.getState().add(type, message)
}

export function ToastContainer() {
  const { toasts, remove } = useToast()
  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map(t => (
        <div
          key={t.id}
          className={`flex items-center gap-3 rounded-lg px-4 py-3 shadow-lg text-white text-sm max-w-sm
            ${t.type === 'success' ? 'bg-green-600' : 'bg-red-600'}`}
        >
          {t.type === 'success'
            ? <CheckCircle className="h-4 w-4 shrink-0" />
            : <XCircle className="h-4 w-4 shrink-0" />}
          <span className="flex-1">{t.message}</span>
          <button onClick={() => remove(t.id)}><X className="h-3.5 w-3.5" /></button>
        </div>
      ))}
    </div>
  )
}
