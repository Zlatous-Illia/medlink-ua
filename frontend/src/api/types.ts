// ── Enums ────────────────────────────────────────────────────────────────────

export type UserRole = 'PATIENT' | 'DOCTOR' | 'ADMIN' | 'SUPER_ADMIN'
export type Gender = 'MALE' | 'FEMALE' | 'OTHER'
export type BloodType = 'A+' | 'A-' | 'B+' | 'B-' | 'AB+' | 'AB-' | 'O+' | 'O-' | 'UNKNOWN'
export type AllergySeverity = 'MILD' | 'MODERATE' | 'SEVERE'
export type EncounterStatus = 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED'
export type ReferralStatus = 'ACTIVE' | 'USED' | 'CANCELLED' | 'EXPIRED'
export type DiagnosisType = 'MAIN' | 'COMPLICATION' | 'CONCOMITANT'
export type PrescriptionStatus = 'ACTIVE' | 'COMPLETED' | 'CANCELLED'
export type AppointmentStatus = 'SCHEDULED' | 'CONFIRMED' | 'COMPLETED' | 'CANCELLED' | 'NO_SHOW'
export type GroupBy = 'day' | 'week' | 'month'

// ── Auth ─────────────────────────────────────────────────────────────────────

export interface UserResponse {
  id: string
  email: string
  role: UserRole
  first_name: string
  last_name: string
  middle_name?: string
  phone?: string
  avatar_url?: string
  is_active: boolean
  is_2fa_enabled: boolean
  created_at: string
}

export interface LoginStep1Response {
  message: string
  email: string
  requires_2fa: boolean
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

// ── Patients ─────────────────────────────────────────────────────────────────

export interface PatientAddress {
  street?: string
  city?: string
  region?: string
  zip?: string
}

export interface PatientResponse {
  id: string
  user_id?: string
  tax_id: string
  unzr?: string
  first_name: string
  last_name: string
  middle_name?: string
  birth_date: string
  gender: Gender
  phone?: string
  email?: string
  address?: PatientAddress
  primary_doctor_id?: string
  esoz_person_id?: string
  is_active: boolean
  created_at: string
}

export interface ICD10Summary {
  id: string
  code: string
  name_ua: string
  name_en?: string
}

export interface AllergyResponse {
  id: string
  patient_id: string
  substance: string
  severity: AllergySeverity
  reaction?: string
  created_at: string
}

export interface ChronicDiseaseResponse {
  id: string
  patient_id: string
  icd10_id: string
  diagnosed_at?: string
  notes?: string
  icd10?: ICD10Summary
  created_at: string
}

export interface MedicalCardResponse {
  id: string
  patient_id: string
  blood_type?: BloodType
  height_cm?: number
  weight_kg?: number
  disability_group?: string
  notes?: string
  allergies: AllergyResponse[]
  chronic_diseases: ChronicDiseaseResponse[]
}

export interface AllergenResponse {
  id: string
  code: string
  name_ua: string
  category?: string
  international_name?: string
  component?: string
}

export interface DocumentResponse {
  id: string
  patient_id: string
  file_name: string
  file_url: string
  file_type?: string
  file_size?: number
  created_at: string
}

// ── Encounters ────────────────────────────────────────────────────────────────

export interface DiagnosisResponse {
  id: string
  encounter_id: string
  icd10_id: string
  type: DiagnosisType
  notes?: string
  icd10?: ICD10Summary
}

export interface EncounterResponse {
  id: string
  patient_id: string
  doctor_id: string
  appointment_id?: string
  status: EncounterStatus
  started_at: string
  completed_at?: string
  complaints?: string
  anamnesis?: string
  objective_exam?: string
  treatment_plan?: string
  recommendations?: string
  pdf_url?: string
  diagnoses: DiagnosisResponse[]
}

export interface ICD10SearchResponse {
  id: string
  code: string
  name_ua: string
  name_en?: string
  category?: string
}

export interface ReferralResponse {
  id: string
  encounter_id: string
  patient_id: string
  doctor_id: string
  specialization_id?: string
  reason?: string
  status: ReferralStatus
  esoz_referral_id?: string
  created_at: string
  expires_at?: string
}

export interface MyReferralResponse {
  id: string
  encounter_id: string
  patient_id: string
  doctor_full_name: string
  specialization_name?: string
  reason?: string
  status: ReferralStatus
  esoz_referral_id?: string
  created_at: string
  expires_at?: string
}


// ── Prescriptions ─────────────────────────────────────────────────────────────

export interface DrugResponse {
  id: string
  atc_code?: string
  inn: string
  trade_name?: string
  form?: string
  dosage?: string
}

export interface PrescriptionResponse {
  id: string
  encounter_id: string
  patient_id: string
  doctor_id: string
  drug_id: string
  dosage?: string
  frequency?: string
  duration_days?: number
  quantity?: number
  instructions?: string
  status: PrescriptionStatus
  esoz_request_id?: string
  esoz_request_number?: string
  expires_at?: string
  created_at: string
  drug?: DrugResponse
}

// ── Appointments ──────────────────────────────────────────────────────────────

export interface SpecializationResponse {
  id: string
  name_ua: string
  name_en?: string
  code?: string
}

export interface DoctorListResponse {
  id: string
  user_id: string
  specialization?: SpecializationResponse
  license_number?: string
  experience_years?: number
  bio?: string
  photo_url?: string
  full_name: string
}

export interface SlotResponse {
  slot_datetime: string
  duration_min: number
  is_available: boolean
}

export interface AppointmentResponse {
  id: string
  patient_id: string
  doctor_id: string
  slot_datetime: string
  duration_min: number
  reason?: string
  status: AppointmentStatus
  cancel_reason?: string
  created_at: string
  doctor?: DoctorListResponse
  patient?: PatientResponse
}

export interface AppointmentTodayResponse {
  id: string
  patient_id: string
  slot_datetime: string
  duration_min: number
  reason?: string
  status: AppointmentStatus
  patient?: PatientResponse
}

// ── Patient Cabinet ───────────────────────────────────────────────────────────

export interface UserProfileResponse {
  id: string
  email: string
  first_name: string
  last_name: string
  middle_name?: string
  phone?: string
  avatar_url?: string
  role: UserRole
  patient_id?: string
  created_at: string
}

export interface ICD10Brief {
  code: string
  name_ua: string
}

export interface ChronicDiseaseReadResponse {
  id: string
  diagnosed_at?: string
  notes?: string
  icd10: ICD10Brief
}

export interface AllergyReadResponse {
  id: string
  substance: string
  severity: AllergySeverity
  reaction?: string
  created_at: string
}

export interface MedicalCardReadResponse {
  id: string
  patient_id: string
  blood_type?: BloodType
  height_cm?: number
  weight_kg?: number
  disability_group?: string
  notes?: string
  allergies: AllergyReadResponse[]
  chronic_diseases: ChronicDiseaseReadResponse[]
}

export interface DiagnosisBriefResponse {
  code: string
  name_ua: string
  type: DiagnosisType
}

export interface MyEncounterResponse {
  id: string
  started_at: string
  completed_at?: string
  status: EncounterStatus
  doctor_full_name: string
  diagnoses: DiagnosisBriefResponse[]
  pdf_url?: string
}

export interface DrugBriefResponse {
  id: string
  inn: string
  trade_name?: string
  form?: string
  dosage?: string
}

export interface MyPrescriptionResponse {
  id: string
  drug: DrugBriefResponse
  dosage?: string
  frequency?: string
  duration_days?: number
  instructions?: string
  status: PrescriptionStatus
  esoz_request_number?: string
  created_at: string
  expires_at?: string
}

export interface MyDocumentResponse {
  id: string
  file_name: string
  file_type?: string
  file_url: string
  file_size?: number
  uploaded_at: string
}

export interface MyReferralResponse {
  id: string
  encounter_id: string
  patient_id: string
  doctor_full_name: string
  specialization_name?: string
  reason?: string
  status: ReferralStatus
  esoz_referral_id?: string
  created_at: string
  expires_at?: string
}

// ── Admin ─────────────────────────────────────────────────────────────────────

export interface UserAdminResponse {
  id: string
  email: string
  first_name: string
  last_name: string
  middle_name?: string
  phone?: string
  role: UserRole
  is_active: boolean
  created_at: string
}

export interface UserAdminDetailResponse extends UserAdminResponse {
  audit_events_count: number
}

export interface AuditLogResponse {
  id: string
  user_id?: string
  action: string
  resource?: string
  resource_id?: string
  ip_address?: string
  details?: Record<string, unknown>
  created_at: string
}

export interface SystemStatsResponse {
  users: { total: number; by_role: Record<string, number> }
  patients: { total: number; active: number }
  encounters: { total: number; last_30_days: number }
  prescriptions: { total: number; active: number }
  appointments: { total: number; upcoming: number }
}

// ── Analytics ─────────────────────────────────────────────────────────────────

export interface AppointmentPeriodResponse {
  period: string
  total: number
  cancelled: number
  completed: number
}

export interface TopDiagnosisResponse {
  icd10_code: string
  name_ua: string
  count: number
}

export interface DoctorLoadResponse {
  doctor_id: string
  full_name: string
  specialization?: string
  encounters_count: number
  appointments_count: number
}

export interface PrescriptionPeriodResponse {
  period: string
  total: number
  active: number
  cancelled: number
}

export interface ScheduleResponse {
  id: string
  doctor_id: string
  day_of_week: number
  start_time: string
  end_time: string
  slot_duration: number
  is_active: boolean
}

export interface CancellationRateResponse {
  total_appointments: number
  cancelled: number
  cancellation_rate: number
}

// ── Encounter Summary (from patients history) ─────────────────────────────────

export interface DiagnosisSummary {
  id: string
  icd10_id: string
  type: string
  notes?: string
}

export interface EncounterSummary {
  id: string
  doctor_id: string
  status: string
  started_at: string
  completed_at?: string
  complaints?: string
  diagnoses: DiagnosisSummary[]
}
