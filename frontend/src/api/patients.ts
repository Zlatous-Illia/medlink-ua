import client from './client'
import type {
  PatientResponse,
  MedicalCardResponse,
  AllergyResponse,
  ChronicDiseaseResponse,
  DocumentResponse,
  EncounterSummary,
  AllergenResponse,
  Gender,
  BloodType,
  AllergySeverity,
} from './types'

export const patientsApi = {
  list: (params?: { search?: string; skip?: number; limit?: number }) =>
    client.get<PatientResponse[]>('/patients', { params }),

  get: (id: string) => client.get<PatientResponse>(`/patients/${id}`),

  deactivate: (id: string) => client.delete(`/patients/${id}`),

  create: (data: {
    tax_id: string
    unzr?: string
    first_name: string
    last_name: string
    middle_name?: string
    birth_date: string
    gender: Gender
    phone?: string
    email?: string
    address?: Record<string, string>
    primary_doctor_id?: string
    user_email?: string
  }) => client.post<PatientResponse>('/patients', data),

  update: (id: string, data: Partial<{
    first_name: string
    last_name: string
    middle_name: string
    birth_date: string
    gender: Gender
    phone: string
    email: string
    address: Record<string, string>
    unzr: string
  }>) => client.patch<PatientResponse>(`/patients/${id}`, data),

  getMedicalCard: (id: string) =>
    client.get<MedicalCardResponse>(`/patients/${id}/medical-card`),

  updateMedicalCard: (id: string, data: {
    blood_type?: BloodType
    height_cm?: number
    weight_kg?: number
    disability_group?: string
    notes?: string
  }) => client.put<MedicalCardResponse>(`/patients/${id}/medical-card`, data),

  // Allergies
  addAllergy: (id: string, data: {
    substance: string
    severity: AllergySeverity
    reaction?: string
  }) => client.post<AllergyResponse>(`/patients/${id}/allergies`, data),

  updateAllergy: (id: string, allergyId: string, data: {
    substance?: string
    severity?: AllergySeverity
    reaction?: string
  }) => client.patch<AllergyResponse>(`/patients/${id}/allergies/${allergyId}`, data),

  deleteAllergy: (id: string, allergyId: string) =>
    client.delete(`/patients/${id}/allergies/${allergyId}`),

  // Chronic diseases
  addChronicDisease: (id: string, data: {
    icd10_id: string
    diagnosed_at?: string
    notes?: string
  }) => client.post<ChronicDiseaseResponse>(`/patients/${id}/chronic-diseases`, data),

  updateChronicDisease: (id: string, diseaseId: string, data: {
    diagnosed_at?: string
    notes?: string
  }) => client.patch<ChronicDiseaseResponse>(`/patients/${id}/chronic-diseases/${diseaseId}`, data),

  deleteChronicDisease: (id: string, diseaseId: string) =>
    client.delete(`/patients/${id}/chronic-diseases/${diseaseId}`),

  // Documents
  uploadDocument: (id: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return client.post<DocumentResponse>(`/patients/${id}/documents`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  getDocuments: (id: string) =>
    client.get<DocumentResponse[]>(`/patients/${id}/documents`),

  deleteDocument: (id: string, documentId: string) =>
    client.delete(`/patients/${id}/documents/${documentId}`),

  getHistory: (id: string) =>
    client.get<EncounterSummary[]>(`/patients/${id}/history`),

  // Allergen reference search
  searchAllergens: (q = '') =>
    client.get<AllergenResponse[]>('/patients/allergens/search', { params: { q } }),
}