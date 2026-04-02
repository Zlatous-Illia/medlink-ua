import client from './client'
import type {
  UserProfileResponse,
  MedicalCardReadResponse,
  MyEncounterResponse,
  MyPrescriptionResponse,
  MyDocumentResponse,
  PrescriptionStatus,
} from './types'

export const cabinetApi = {
  getProfile: () => client.get<UserProfileResponse>('/me'),

  updateProfile: (data: {
    first_name?: string
    last_name?: string
    middle_name?: string
    phone?: string
  }) => client.patch<UserProfileResponse>('/me', data),

  uploadAvatar: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return client.post<UserProfileResponse>('/me/avatar', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  getMedicalCard: () => client.get<MedicalCardReadResponse>('/me/medical-card'),

  getEncounters: () => client.get<MyEncounterResponse[]>('/me/encounters'),

  getPrescriptions: (status?: PrescriptionStatus) =>
    client.get<MyPrescriptionResponse[]>('/me/prescriptions', {
      params: status ? { status } : undefined,
    }),

  getDocuments: () => client.get<MyDocumentResponse[]>('/me/documents'),

  changePassword: (current_password: string, new_password: string) =>
    client.patch('/me/change-password', { current_password, new_password }),
}
