import client from './client'
import type {
  UserAdminResponse,
  UserAdminDetailResponse,
  AuditLogResponse,
  SystemStatsResponse,
  UserRole,
} from './types'

export const adminApi = {
  listUsers: (params?: {
    role?: UserRole
    is_active?: boolean
    search?: string
    skip?: number
    limit?: number
  }) => client.get<UserAdminResponse[]>('/admin/users', { params }),

  getUser: (id: string) =>
    client.get<UserAdminDetailResponse>(`/admin/users/${id}`),

  updateUser: (id: string, data: { is_active?: boolean; role?: UserRole }) =>
    client.patch<UserAdminDetailResponse>(`/admin/users/${id}`, data),

  deactivateUser: (id: string) =>
    client.post<UserAdminDetailResponse>(`/admin/users/${id}/deactivate`),

  getAuditLogs: (params?: {
    user_id?: string
    action?: string
    resource?: string
    date_from?: string
    date_to?: string
    skip?: number
    limit?: number
  }) => client.get<AuditLogResponse[]>('/admin/audit-logs', { params }),

  getStats: () => client.get<SystemStatsResponse>('/admin/stats'),
}
