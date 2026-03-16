import uuid
import enum
from datetime import datetime, date, timezone
from sqlalchemy import String, Boolean, DateTime, Date, Enum as SAEnum, SmallInteger, Numeric, Text, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.user import utcnow


class Gender(str, enum.Enum):
    MALE   = "MALE"
    FEMALE = "FEMALE"
    OTHER  = "OTHER"


class BloodType(str, enum.Enum):
    A_POS   = "A+"
    A_NEG   = "A-"
    B_POS   = "B+"
    B_NEG   = "B-"
    AB_POS  = "AB+"
    AB_NEG  = "AB-"
    O_POS   = "O+"
    O_NEG   = "O-"
    UNKNOWN = "UNKNOWN"


class SmokingStatus(str, enum.Enum):
    NEVER   = "NEVER"
    FORMER  = "FORMER"
    CURRENT = "CURRENT"
    UNKNOWN = "UNKNOWN"


class AllergySeverity(str, enum.Enum):
    MILD     = "MILD"
    MODERATE = "MODERATE"
    SEVERE   = "SEVERE"


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True)
    tax_id: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)   # РНОКПП
    unzr: Mapped[str | None] = mapped_column(String(14), unique=True, index=True)              # УНЗР
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    middle_name: Mapped[str | None] = mapped_column(String(100))
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[Gender] = mapped_column(SAEnum(Gender), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(255))
    address: Mapped[dict | None] = mapped_column(JSONB)        # {street, city, region, zip}
    primary_doctor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("doctors.id"))
    esoz_person_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    # Relationships
    medical_card: Mapped["MedicalCard | None"] = relationship(back_populates="patient", uselist=False, cascade="all, delete-orphan")
    allergies: Mapped[list["Allergy"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    chronic_diseases: Mapped[list["ChronicDisease"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    documents: Mapped[list["PatientDocument"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    encounters: Mapped[list["Encounter"]] = relationship(back_populates="patient")
    prescriptions: Mapped[list["Prescription"]] = relationship(back_populates="patient")
    appointments: Mapped[list["Appointment"]] = relationship(back_populates="patient")

    @property
    def full_name(self) -> str:
        parts = [self.last_name, self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        return " ".join(parts)

    @property
    def age(self) -> int:
        today = date.today()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )


class MedicalCard(Base):
    __tablename__ = "medical_cards"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id"), unique=True, nullable=False)
    blood_type: Mapped[BloodType | None] = mapped_column(SAEnum(BloodType), default=BloodType.UNKNOWN)
    height_cm: Mapped[int | None] = mapped_column(SmallInteger)
    weight_kg: Mapped[float | None] = mapped_column(Numeric(5, 1))
    smoking_status: Mapped[SmokingStatus] = mapped_column(SAEnum(SmokingStatus), default=SmokingStatus.UNKNOWN)
    notes: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    patient: Mapped["Patient"] = relationship(back_populates="medical_card")


class Allergy(Base):
    __tablename__ = "allergies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    substance: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[AllergySeverity] = mapped_column(SAEnum(AllergySeverity), nullable=False)
    reaction: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    patient: Mapped["Patient"] = relationship(back_populates="allergies")


class ChronicDisease(Base):
    __tablename__ = "chronic_diseases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    icd10_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("icd10_codes.id"), nullable=False)
    diagnosed_at: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    patient: Mapped["Patient"] = relationship(back_populates="chronic_diseases")
    icd10: Mapped["ICD10Code"] = relationship()


class PatientDocument(Base):
    __tablename__ = "patient_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50))
    file_size: Mapped[int | None] = mapped_column()
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    patient: Mapped["Patient"] = relationship(back_populates="documents")


# ─── Forward refs (imported in models __init__) ─────────────────────────────
from app.models.clinical import Encounter, Prescription  # noqa: E402
from app.models.scheduling import Appointment            # noqa: E402
from app.models.reference import ICD10Code               # noqa: E402
from app.models.doctor import Doctor                     # noqa: E402
