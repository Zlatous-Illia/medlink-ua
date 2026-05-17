import client from './client'
import type { PrescriptionResponse, DrugResponse, PrescriptionStatus } from './types'

export const prescriptionsApi = {
  create: (data: {
    encounter_id: string
    drug_id: string
    dosage?: string
    frequency?: string
    duration_days?: number
    quantity?: number
    instructions?: string
  }) => client.post<PrescriptionResponse>('/prescriptions', data),

  searchDrugs: (q = '', limit = 10) =>
    client.get<DrugResponse[]>('/prescriptions/drugs/search', { params: { q, limit } }),

  getByPatient: (patientId: string, status?: PrescriptionStatus) =>
    client.get<PrescriptionResponse[]>(`/prescriptions/patients/${patientId}/prescriptions`, {
      params: status ? { status } : undefined,
    }),

  get: (id: string) => client.get<PrescriptionResponse>(`/prescriptions/${id}`),

  cancel: (id: string, reason: string) =>
    client.patch<PrescriptionResponse>(`/prescriptions/${id}/cancel`, { reason }),
}
