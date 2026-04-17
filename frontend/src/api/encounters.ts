import client from './client'
import type {
  EncounterResponse,
  DiagnosisResponse,
  ICD10SearchResponse,
  AppointmentTodayResponse,
  DiagnosisType,
  ReferralResponse,
} from './types'

export const encountersApi = {
  todayAppointments: () =>
    client.get<AppointmentTodayResponse[]>('/appointments/today'),

  create: (data: { patient_id: string; appointment_id?: string }) =>
    client.post<EncounterResponse>('/encounters', data),

  get: (id: string) => client.get<EncounterResponse>(`/encounters/${id}`),

  update: (id: string, data: {
    complaints?: string
    anamnesis?: string
    objective_exam?: string
    treatment_plan?: string
    recommendations?: string
  }) => client.patch<EncounterResponse>(`/encounters/${id}`, data),

  complete: (id: string) =>
    client.post<EncounterResponse>(`/encounters/${id}/complete`),

  getPdfUrl: (id: string) => `/api/v1/encounters/${id}/pdf`,

  addDiagnosis: (id: string, data: {
    icd10_id: string
    type?: DiagnosisType
    notes?: string
  }) => client.post<DiagnosisResponse>(`/encounters/${id}/diagnoses`, data),

  getByPatient: (patientId: string) =>
    client.get<EncounterResponse[]>(`/encounters/patients/${patientId}/encounters`),

  searchICD10: (q: string, limit = 10) =>
    client.get<ICD10SearchResponse[]>('/icd10/search', { params: { q, limit } }),

  createReferral: (encounterId: string, data: {
    specialization_id?: string
    reason?: string
  }) => client.post<ReferralResponse>(`/encounters/${encounterId}/referrals`, {
    ...data,
    encounter_id: encounterId,
  }),

  getReferralsByPatient: (patientId: string) =>
    client.get<ReferralResponse[]>(`/encounters/patients/${patientId}/referrals`),
}
