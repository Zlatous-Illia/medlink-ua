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

            if settings.DEBUG:
                print(
                    f"[DEV] Reminder {reminder_type} for appointment {appointment_id}: "
                    f"{patient_email} at {slot_datetime}"
                )

            # TODO: real email via fastapi-mail when SMTP is configured

            if reminder_type == "24h":
                appointment.reminder_24h = True
            elif reminder_type == "1h":
                appointment.reminder_1h = True
            session.commit()

    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
