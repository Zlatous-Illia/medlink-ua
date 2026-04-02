import client from './client'
import type {
  AppointmentPeriodResponse,
  TopDiagnosisResponse,
  DoctorLoadResponse,
  PrescriptionPeriodResponse,
  CancellationRateResponse,
  GroupBy,
} from './types'

interface DateRange {
  date_from?: string
  date_to?: string
}

export const analyticsApi = {
  appointments: (params: DateRange & { group_by?: GroupBy }) =>
    client.get<AppointmentPeriodResponse[]>('/analytics/appointments', { params }),

  topDiagnoses: (params: DateRange & { doctor_id?: string }) =>
    client.get<TopDiagnosisResponse[]>('/analytics/diagnoses/top10', { params }),

  doctorLoad: (params: DateRange) =>
    client.get<DoctorLoadResponse[]>('/analytics/doctors/load', { params }),

  prescriptions: (params: DateRange & { group_by?: GroupBy }) =>
    client.get<PrescriptionPeriodResponse[]>('/analytics/prescriptions', { params }),

  cancellationRate: (params: DateRange & { doctor_id?: string }) =>
    client.get<CancellationRateResponse>('/analytics/appointments/cancellation-rate', { params }),
}
