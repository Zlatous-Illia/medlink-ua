import client from './client'
import type { LoginStep1Response, TokenResponse, UserResponse } from './types'

export const authApi = {
  register: (data: {
    email: string
    password: string
    first_name: string
    last_name: string
    middle_name?: string
    phone?: string
    role?: string
  }) => client.post<UserResponse>('/auth/register', data),

  login: (email: string, password: string) =>
    client.post<LoginStep1Response>('/auth/login', { email, password }),

  verify2FA: (email: string, otp_code: string) =>
    client.post<TokenResponse>('/auth/login/2fa', { email, otp_code }),

  refresh: (refresh_token: string) =>
    client.post<TokenResponse>('/auth/refresh', { refresh_token }),

  logout: (refresh_token: string) =>
    client.post('/auth/logout', { refresh_token }),

  me: () => client.get<UserResponse>('/auth/me'),

  forgotPassword: (email: string) =>
    client.post('/auth/forgot-password', { email }),

  resetPassword: (token: string, new_password: string) =>
    client.post('/auth/reset-password', { token, new_password }),
}
