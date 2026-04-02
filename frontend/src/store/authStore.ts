import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { initApiClient } from '../api/client'
import type { UserRole } from '../api/types'

export interface AuthUser {
  id: string
  email: string
  first_name: string
  last_name: string
  middle_name?: string
  role: UserRole
  avatar_url?: string
  is_active: boolean
}

interface AuthState {
  user: AuthUser | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  pendingEmail: string | null
  setUser: (user: AuthUser) => void
  setTokens: (access: string, refresh: string) => void
  setPendingEmail: (email: string) => void
  login: (user: AuthUser, access: string, refresh: string) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      pendingEmail: null,
      setUser: user => set({ user }),
      setTokens: (accessToken, refreshToken) =>
        set({ accessToken, refreshToken, isAuthenticated: true }),
      setPendingEmail: email => set({ pendingEmail: email }),
      login: (user, accessToken, refreshToken) =>
        set({ user, accessToken, refreshToken, isAuthenticated: true }),
      logout: () =>
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
          pendingEmail: null,
        }),
    }),
    {
      name: 'medlink-auth',
      partialize: state => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)

// Wire up the API client with store functions
initApiClient(
  () => useAuthStore.getState().accessToken,
  () => useAuthStore.getState().refreshToken,
  (a, r) => useAuthStore.getState().setTokens(a, r),
  () => useAuthStore.getState().logout()
)
