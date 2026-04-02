import client from './client'
import type {
  AppointmentResponse,
  DoctorListResponse,
  SlotResponse,
  ScheduleResponse,
} from './types'

export const appointmentsApi = {
  list: (params?: { skip?: number; limit?: number }) =>
    client.get<AppointmentResponse[]>('/appointments', { params }),

  create: (data: { doctor_id: string; slot_datetime: string; reason?: string }) =>
    client.post<AppointmentResponse>('/appointments', data),

  get: (id: string) => client.get<AppointmentResponse>(`/appointments/${id}`),

  cancel: (id: string, reason?: string) =>
    client.patch<AppointmentResponse>(`/appointments/${id}/cancel`, { reason }),

  listDoctors: (params?: { specialization_id?: string }) =>
    client.get<DoctorListResponse[]>('/doctors', { params }),

  getSlots: (doctorId: string, date: string) =>
    client.get<SlotResponse[]>(`/doctors/${doctorId}/slots`, { params: { date } }),

  getDoctorSchedule: (doctorId: string) =>
    client.get<ScheduleResponse[]>(`/doctors/${doctorId}/schedule`),

  setDoctorSchedule: (doctorId: string, data: {
    day_of_week: number
    start_time: string
    end_time: string
    slot_duration?: number
  }) => client.post<ScheduleResponse>(`/doctors/${doctorId}/schedule`, data),
}
