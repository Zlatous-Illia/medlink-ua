import { type ReactNode, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Menu, X, LogOut, Stethoscope } from 'lucide-react'
import { Sidebar } from './Sidebar'
import { useAuthStore } from '../../store/authStore'
import { authApi } from '../../api/auth'
import { ToastContainer } from '../shared/Toast'

export function AppShell({ children }: { children: ReactNode }) {
  const { user, refreshToken, logout } = useAuthStore()
  const navigate = useNavigate()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  async function handleLogout() {
    try {
      if (refreshToken) await authApi.logout(refreshToken)
    } catch { /* ignore */ }
    logout()
    navigate('/login')
  }

  if (!user) return null

  const initials = `${user.first_name[0]}${user.last_name[0]}`.toUpperCase()

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/30 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed lg:static inset-y-0 left-0 z-40 flex w-60 flex-col bg-white border-r border-gray-200
          transition-transform duration-200 ease-in-out
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}`}
      >
        {/* Logo */}
        <div className="flex h-14 items-center gap-2 px-4 border-b border-gray-200">
          <Stethoscope className="h-6 w-6 text-blue-600" />
          <span className="text-base font-bold text-gray-900">MedLink UA</span>
          <button className="ml-auto lg:hidden" onClick={() => setSidebarOpen(false)}>
            <X className="h-4 w-4 text-gray-500" />
          </button>
        </div>

        {/* Nav */}
        <div className="flex-1 overflow-y-auto py-2">
          <Sidebar role={user.role} />
        </div>

        {/* User footer */}
        <div className="border-t border-gray-200 p-3">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-700">
              {initials}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-medium text-gray-900">
                {user.first_name} {user.last_name}
              </p>
              <p className="truncate text-xs text-gray-500">{user.email}</p>
            </div>
            <button
              onClick={handleLogout}
              title="Вийти"
              className="text-gray-400 hover:text-red-500 transition-colors"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Topbar (mobile) */}
        <header className="flex h-14 items-center gap-4 border-b border-gray-200 bg-white px-4 lg:hidden">
          <button onClick={() => setSidebarOpen(true)}>
            <Menu className="h-5 w-5 text-gray-600" />
          </button>
          <Stethoscope className="h-5 w-5 text-blue-600" />
          <span className="font-semibold text-gray-900">MedLink UA</span>
        </header>

        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>

      <ToastContainer />
    </div>
  )
}
