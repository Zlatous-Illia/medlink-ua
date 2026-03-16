# Import all models here so Alembic can discover them via Base.metadata
from app.models.user import User, RefreshToken, AuditLog
from app.models.reference import ICD10Code, Drug, Specialization
from app.models.doctor import Doctor
from app.models.patient import Patient, MedicalCard, Allergy, ChronicDisease, PatientDocument
from app.models.scheduling import Schedule, Appointment
from app.models.clinical import Encounter, Diagnosis, Prescription, Referral

__all__ = [
    "User", "RefreshToken", "AuditLog",
    "ICD10Code", "Drug", "Specialization",
    "Doctor",
    "Patient", "MedicalCard", "Allergy", "ChronicDisease", "PatientDocument",
    "Schedule", "Appointment",
    "Encounter", "Diagnosis", "Prescription", "Referral",
]
