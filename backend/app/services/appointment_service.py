from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta, date, time as time_type
from typing import Optional

import redis.asyncio as aioredis
from fastapi import HTTPException
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.reference import Specialization
from app.models.scheduling import Schedule, Appointment, AppointmentStatus
from app.models.user import AuditLog, User, UserRole
from app.schemas.appointments import (
    AppointmentCreate, AppointmentResponse, AppointmentCancelRequest,
    DoctorListResponse, SlotResponse, ScheduleCreate, ScheduleResponse,
)


class AppointmentService:

    def __init__(self, db: AsyncSession, redis: aioredis.Redis):
        self.db = db
        self.redis = redis

    async def list_doctors(
        self,
        specialization_id: Optional[uuid.UUID],
        skip: int,
        limit: int,
    ) -> list[DoctorListResponse]:
        query = (
            select(Doctor)
            .where(Doctor.is_active == True)
            .options(joinedload(Doctor.user), joinedload(Doctor.specialization))
            .offset(skip)
            .limit(limit)
        )
        if specialization_id:
            query = query.where(Doctor.specialization_id == specialization_id)

        result = await self.db.execute(query)
        doctors = result.unique().scalars().all()
        return [
            DoctorListResponse(
                id=d.id,
                user_id=d.user_id,
                specialization=d.specialization,
                license_number=d.license_number,
                experience_years=d.experience_years,
                bio=d.bio,
                photo_url=d.photo_url,
                full_name=d.user.full_name if d.user else "",
            )
            for d in doctors
        ]

    async def get_doctor_slots(self, doctor_id: uuid.UUID, target_date: date) -> list[SlotResponse]:
        doc_result = await self.db.execute(
            select(Doctor).where(Doctor.id == doctor_id, Doctor.is_active == True)
        )
        doctor = doc_result.scalar_one_or_none()
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")

        schedule_result = await self.db.execute(
            select(Schedule).where(
                Schedule.doctor_id == doctor_id,
                Schedule.day_of_week == target_date.weekday(),
                Schedule.is_active == True,
            )
        )
        schedule = schedule_result.scalar_one_or_none()
        if not schedule:
            return []

        slots = []
        current = datetime.combine(target_date, schedule.start_time, tzinfo=timezone.utc)
        end_dt = datetime.combine(target_date, schedule.end_time, tzinfo=timezone.utc)
        duration = timedelta(minutes=schedule.slot_duration)

        while current + duration <= end_dt:
            slot_end = current + duration
            busy_result = await self.db.execute(
                select(Appointment).where(
                    and_(
                        Appointment.doctor_id == doctor_id,
                        Appointment.slot_datetime >= current,
                        Appointment.slot_datetime < slot_end,
                        Appointment.status != AppointmentStatus.CANCELLED,
                    )
                )
            )
            busy = busy_result.scalar_one_or_none()
            slots.append(SlotResponse(
                slot_datetime=current,
                duration_min=schedule.slot_duration,
                is_available=(busy is None),
            ))
            current += duration

        return slots

    async def create_appointment(self, data: AppointmentCreate, patient_user: User) -> AppointmentResponse:
        patient_result = await self.db.execute(
            select(Patient).where(Patient.user_id == patient_user.id)
        )
        patient = patient_result.scalar_one_or_none()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient profile not found")

        # Optimistic slot locking via Redis
        lock_key = f"slot_lock:{data.doctor_id}:{data.slot_datetime.isoformat()}"
        locked = await self.redis.set(lock_key, "1", nx=True, ex=10)
        if not locked:
            raise HTTPException(status_code=409, detail="Slot is being booked by another user")

        try:
            existing_result = await self.db.execute(
                select(Appointment).where(
                    and_(
                        Appointment.doctor_id == data.doctor_id,
                        Appointment.slot_datetime == data.slot_datetime,
                        Appointment.status != AppointmentStatus.CANCELLED,
                    )
                )
            )
            if existing_result.scalar_one_or_none():
                raise HTTPException(status_code=409, detail="Slot already booked")

            appointment = Appointment(
                patient_id=patient.id,
                doctor_id=data.doctor_id,
                slot_datetime=data.slot_datetime,
                reason=data.reason,
                status=AppointmentStatus.SCHEDULED,
            )
            self.db.add(appointment)
            await self.db.flush()

            # Schedule Celery reminders
            try:
                from app.workers.email_tasks import send_reminder
                eta_24h = data.slot_datetime - timedelta(hours=24)
                eta_1h = data.slot_datetime - timedelta(hours=1)
                if eta_24h > datetime.now(timezone.utc):
                    send_reminder.apply_async(args=[str(appointment.id), "24h"], eta=eta_24h)
                if eta_1h > datetime.now(timezone.utc):
                    send_reminder.apply_async(args=[str(appointment.id), "1h"], eta=eta_1h)
            except Exception:
                pass

            self.db.add(AuditLog(
                user_id=patient_user.id, action="CREATE_APPOINTMENT",
                resource="appointments", resource_id=appointment.id,
            ))
            await self.db.commit()

            result = await self.db.execute(
                select(Appointment)
                .where(Appointment.id == appointment.id)
                .options(
                    joinedload(Appointment.doctor).joinedload(Doctor.user),
                    joinedload(Appointment.doctor).joinedload(Doctor.specialization),
                    joinedload(Appointment.patient),
                )
            )
            appointment = result.unique().scalar_one()
            return self._appointment_to_response(appointment)
        finally:
            await self.redis.delete(lock_key)

    async def list_appointments(self, requesting_user: User, skip: int, limit: int) -> list[AppointmentResponse]:
        query = (
            select(Appointment)
            .options(
                joinedload(Appointment.doctor).joinedload(Doctor.user),
                joinedload(Appointment.doctor).joinedload(Doctor.specialization),
                joinedload(Appointment.patient),
            )
            .order_by(Appointment.slot_datetime.desc())
            .offset(skip)
            .limit(limit)
        )

        if requesting_user.role in (UserRole.DOCTOR, UserRole.ADMIN, UserRole.SUPER_ADMIN):
            if requesting_user.role == UserRole.DOCTOR:
                doc_result = await self.db.execute(
                    select(Doctor).where(Doctor.user_id == requesting_user.id)
                )
                doctor = doc_result.scalar_one_or_none()
                if doctor:
                    query = query.where(Appointment.doctor_id == doctor.id)
        else:
            patient_result = await self.db.execute(
                select(Patient).where(Patient.user_id == requesting_user.id)
            )
            patient = patient_result.scalar_one_or_none()
            if patient:
                query = query.where(Appointment.patient_id == patient.id)

        result = await self.db.execute(query)
        appointments = result.unique().scalars().all()
        return [self._appointment_to_response(a) for a in appointments]

    async def get_appointment(self, appointment_id: uuid.UUID, requesting_user: User) -> AppointmentResponse:
        result = await self.db.execute(
            select(Appointment)
            .where(Appointment.id == appointment_id)
            .options(
                joinedload(Appointment.doctor).joinedload(Doctor.user),
                joinedload(Appointment.doctor).joinedload(Doctor.specialization),
                joinedload(Appointment.patient),
            )
        )
        appointment = result.unique().scalar_one_or_none()
        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")

        if requesting_user.role == UserRole.DOCTOR:
            doc_result = await self.db.execute(
                select(Doctor).where(Doctor.user_id == requesting_user.id)
            )
            doctor = doc_result.scalar_one_or_none()
            if not doctor or appointment.doctor_id != doctor.id:
                raise HTTPException(status_code=403, detail="Access denied")
        elif requesting_user.role == UserRole.PATIENT:
            patient_result = await self.db.execute(
                select(Patient).where(Patient.user_id == requesting_user.id)
            )
            patient = patient_result.scalar_one_or_none()
            if not patient or appointment.patient_id != patient.id:
                raise HTTPException(status_code=403, detail="Access denied")

        return self._appointment_to_response(appointment)

    async def cancel_appointment(
        self,
        appointment_id: uuid.UUID,
        data: AppointmentCancelRequest,
        requesting_user: User,
    ) -> AppointmentResponse:
        result = await self.db.execute(
            select(Appointment)
            .where(Appointment.id == appointment_id)
            .options(
                joinedload(Appointment.doctor).joinedload(Doctor.user),
                joinedload(Appointment.doctor).joinedload(Doctor.specialization),
                joinedload(Appointment.patient),
            )
        )
        appointment = result.unique().scalar_one_or_none()
        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")

        if requesting_user.role == UserRole.DOCTOR:
            doc_result = await self.db.execute(
                select(Doctor).where(Doctor.user_id == requesting_user.id)
            )
            doctor = doc_result.scalar_one_or_none()
            if not doctor or appointment.doctor_id != doctor.id:
                raise HTTPException(status_code=403, detail="Access denied")
        elif requesting_user.role == UserRole.PATIENT:
            patient_result = await self.db.execute(
                select(Patient).where(Patient.user_id == requesting_user.id)
            )
            patient = patient_result.scalar_one_or_none()
            if not patient or appointment.patient_id != patient.id:
                raise HTTPException(status_code=403, detail="Access denied")

        if appointment.status in (AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED):
            raise HTTPException(status_code=400, detail="Appointment cannot be cancelled in its current status")

        appointment.status = AppointmentStatus.CANCELLED
        appointment.cancelled_by = requesting_user.id
        appointment.cancel_reason = data.reason

        self.db.add(AuditLog(
            user_id=requesting_user.id, action="CANCEL_APPOINTMENT",
            resource="appointments", resource_id=appointment.id,
        ))
        await self.db.commit()
        await self.db.refresh(appointment)
        return self._appointment_to_response(appointment)

    async def create_schedule(self, doctor_id: uuid.UUID, data: ScheduleCreate, admin: User) -> ScheduleResponse:
        doc_result = await self.db.execute(
            select(Doctor).where(Doctor.id == doctor_id)
        )
        doctor = doc_result.scalar_one_or_none()
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")

        existing_result = await self.db.execute(
            select(Schedule).where(
                Schedule.doctor_id == doctor_id,
                Schedule.day_of_week == data.day_of_week,
                Schedule.is_active == True,
            )
        )
        existing = existing_result.scalars().all()
        for s in existing:
            if not (data.end_time <= s.start_time or data.start_time >= s.end_time):
                raise HTTPException(status_code=409, detail="Schedule overlaps with existing schedule for this day")

        schedule = Schedule(
            doctor_id=doctor_id,
            day_of_week=data.day_of_week,
            start_time=data.start_time,
            end_time=data.end_time,
            slot_duration=data.slot_duration,
        )
        self.db.add(schedule)
        await self.db.commit()
        await self.db.refresh(schedule)
        return ScheduleResponse.model_validate(schedule)

    async def get_schedule(self, doctor_id: uuid.UUID) -> list[ScheduleResponse]:
        result = await self.db.execute(
            select(Schedule).where(
                Schedule.doctor_id == doctor_id,
                Schedule.is_active == True,
            )
        )
        schedules = result.scalars().all()
        return [ScheduleResponse.model_validate(s) for s in schedules]

    def _appointment_to_response(self, appointment: Appointment) -> AppointmentResponse:
        doctor_resp = None
        if appointment.doctor:
            d = appointment.doctor
            doctor_resp = DoctorListResponse(
                id=d.id,
                user_id=d.user_id,
                specialization=d.specialization,
                license_number=d.license_number,
                experience_years=d.experience_years,
                bio=d.bio,
                photo_url=d.photo_url,
                full_name=d.user.full_name if d.user else "",
            )
        from app.schemas.patients import PatientResponse
        patient_resp = PatientResponse.model_validate(appointment.patient) if appointment.patient else None
        return AppointmentResponse(
            id=appointment.id,
            patient_id=appointment.patient_id,
            doctor_id=appointment.doctor_id,
            slot_datetime=appointment.slot_datetime,
            duration_min=appointment.duration_min,
            reason=appointment.reason,
            status=appointment.status,
            cancel_reason=appointment.cancel_reason,
            created_at=appointment.created_at,
            doctor=doctor_resp,
            patient=patient_resp,
        )
