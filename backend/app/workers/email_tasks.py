from app.workers.celery_app import celery_app


@celery_app.task(name="send_reminder", bind=True, max_retries=3)
def send_reminder(self, appointment_id: str, reminder_type: str):
    """Send appointment reminder email. reminder_type: '24h' or '1h'."""
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session, joinedload
        from app.core.config import settings
        from app.models.scheduling import Appointment, AppointmentStatus
        from app.models.doctor import Doctor

        engine = create_engine(settings.DATABASE_URL_SYNC)
        with Session(engine) as session:
            import uuid
            appointment = session.get(Appointment, uuid.UUID(appointment_id))
            if not appointment:
                return

            if appointment.status not in (AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED):
                return

            patient = appointment.patient if appointment.patient else None
            patient_email = patient.email if patient else None
            slot_datetime = appointment.slot_datetime

            # Always log to console for dev visibility:
            print(
                f"[DEV] Reminder ({reminder_type}) for appointment {appointment_id}: "
                f"patient={patient_email} at {slot_datetime}"
            )

            # Send real email (skipped when SMTP credentials are not set):
            if patient_email:
                import asyncio
                from app.services.email_service import send_appointment_reminder
                patient_name = f"{patient.first_name} {patient.last_name}" if patient else "Пацієнт"
                doctor_name = "Лікар"
                if appointment.doctor:
                    d = appointment.doctor
                    doctor_name = f"{d.first_name} {d.last_name}" if hasattr(d, "first_name") else doctor_name
                asyncio.run(send_appointment_reminder(
                    email=patient_email,
                    patient_name=patient_name,
                    doctor_name=doctor_name,
                    slot_datetime=str(slot_datetime),
                    reminder_type=reminder_type,
                ))

            if reminder_type == "24h":
                appointment.reminder_24h = True
            elif reminder_type == "1h":
                appointment.reminder_1h = True
            session.commit()

    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
