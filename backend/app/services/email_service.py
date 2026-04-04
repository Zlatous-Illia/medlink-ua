"""
Email service using fastapi-mail.

Always prints to console (for dev visibility), and sends real emails
when SMTP credentials are configured in settings.
"""
from __future__ import annotations

from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType

from app.core.config import settings


def _get_mail_config() -> ConnectionConfig | None:
    """Return ConnectionConfig if SMTP credentials are set, else None."""
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        return None
    return ConnectionConfig(
        MAIL_USERNAME=settings.SMTP_USER,
        MAIL_PASSWORD=settings.SMTP_PASSWORD,
        MAIL_FROM=settings.EMAIL_FROM,
        MAIL_FROM_NAME=settings.EMAIL_FROM_NAME,
        MAIL_PORT=settings.SMTP_PORT,
        MAIL_SERVER=settings.SMTP_HOST,
        MAIL_STARTTLS=settings.SMTP_TLS,
        MAIL_SSL_TLS=False,
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True,
    )


async def _send(subject: str, recipients: list[str], body: str) -> None:
    """Send email if SMTP is configured; silently skip otherwise."""
    config = _get_mail_config()
    if not config:
        return
    message = MessageSchema(
        subject=subject,
        recipients=recipients,
        body=body,
        subtype=MessageType.html,
    )
    try:
        fm = FastMail(config)
        await fm.send_message(message)
    except Exception as exc:
        print(f"[EMAIL] Failed to send to {recipients}: {exc}")


# ─── OTP ─────────────────────────────────────────────────────────────────────

async def send_otp(email: str, first_name: str, otp: str) -> None:
    """Send login OTP code to user. Always prints to console."""
    print(f"[DEV] OTP email → {email} | code: {otp}")
    subject = f"[{settings.APP_NAME}] Ваш код підтвердження"
    body = f"""
<p>Привіт, <strong>{first_name}</strong>!</p>
<p>Ваш код підтвердження для входу в систему:</p>
<h2 style="letter-spacing:6px; font-size:32px;">{otp}</h2>
<p>Код дійсний протягом 5 хвилин. Нікому його не повідомляйте.</p>
<hr/>
<p style="color:#888; font-size:12px;">{settings.APP_NAME} &mdash; Електронна медична система</p>
"""
    await _send(subject, [email], body)


# ─── Password Reset ───────────────────────────────────────────────────────────

async def send_password_reset(email: str, first_name: str, token: str) -> None:
    """Send password reset link. Always prints to console."""
    reset_url = f"http://localhost:3000/reset-password?token={token}"
    print(f"[DEV] Password reset email → {email} | token: {token} | url: {reset_url}")
    subject = f"[{settings.APP_NAME}] Скидання паролю"
    body = f"""
<p>Привіт, <strong>{first_name}</strong>!</p>
<p>Отримано запит на скидання паролю для вашого облікового запису.</p>
<p><a href="{reset_url}" style="background:#2563eb;color:#fff;padding:10px 20px;
   border-radius:6px;text-decoration:none;display:inline-block;">
   Скинути пароль
</a></p>
<p>Або скопіюйте посилання вручну:<br/><code>{reset_url}</code></p>
<p>Посилання дійсне протягом 1 години.</p>
<p>Якщо ви не надсилали цей запит — просто проігноруйте цей лист.</p>
<hr/>
<p style="color:#888; font-size:12px;">{settings.APP_NAME} &mdash; Електронна медична система</p>
"""
    await _send(subject, [email], body)


# ─── Appointment Reminder ────────────────────────────────────────────────────

async def send_appointment_reminder(
    email: str,
    patient_name: str,
    doctor_name: str,
    slot_datetime: str,
    reminder_type: str,
) -> None:
    """Send appointment reminder (24h or 1h before). Always prints to console."""
    time_label = "завтра" if reminder_type == "24h" else "через 1 годину"
    print(
        f"[DEV] Reminder email ({reminder_type}) → {email} | "
        f"patient: {patient_name} | doctor: {doctor_name} | time: {slot_datetime}"
    )
    subject = f"[{settings.APP_NAME}] Нагадування про запис до лікаря"
    body = f"""
<p>Привіт, <strong>{patient_name}</strong>!</p>
<p>Нагадуємо, що <strong>{time_label}</strong> у вас запис до лікаря:</p>
<ul>
  <li><strong>Лікар:</strong> {doctor_name}</li>
  <li><strong>Час:</strong> {slot_datetime}</li>
</ul>
<p>Якщо вам потрібно скасувати запис — зробіть це заздалегідь у кабінеті пацієнта.</p>
<hr/>
<p style="color:#888; font-size:12px;">{settings.APP_NAME} &mdash; Електронна медична система</p>
"""
    await _send(subject, [email], body)
