import uuid
import enum
from datetime import datetime, timezone, timedelta
from sqlalchemy import String, Boolean, DateTime, Enum as SAEnum, SmallInteger, Text, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.user import utcnow


class EncounterStatus(str, enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED   = "COMPLETED"
    CANCELLED   = "CANCELLED"


class DiagnosisType(str, enum.Enum):
    MAIN          = "MAIN"
    COMPLICATION  = "COMPLICATION"
    CONCOMITANT   = "CONCOMITANT"


class PrescriptionStatus(str, enum.Enum):
    ACTIVE    = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ReferralStatus(str, enum.Enum):
    ACTIVE    = "ACTIVE"
    USED      = "USED"
    EXPIRED   = "EXPIRED"
    CANCELLED = "CANCELLED"


class Encounter(Base):
    """Прийом лікаря."""
    __tablename__ = "encounters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    doctor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("doctors.id"), nullable=False)
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("appointments.id"))
    status: Mapped[EncounterStatus] = mapped_column(SAEnum(EncounterStatus), default=EncounterStatus.IN_PROGRESS)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    complaints: Mapped[str | None] = mapped_column(Text)
    anamnesis: Mapped[str | None] = mapped_column(Text)
    objective_exam: Mapped[str | None] = mapped_column(Text)
    treatment_plan: Mapped[str | None] = mapped_column(Text)
    recommendations: Mapped[str | None] = mapped_column(Text)
    pdf_url: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # Relationships
    patient: Mapped["Patient"] = relationship(back_populates="encounters")
    doctor: Mapped["Doctor"] = relationship(back_populates="encounters")
    diagnoses: Mapped[list["Diagnosis"]] = relationship(back_populates="encounter", cascade="all, delete-orphan")
    prescriptions: Mapped[list["Prescription"]] = relationship(back_populates="encounter")
    referrals: Mapped[list["Referral"]] = relationship(back_populates="encounter")


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    encounter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False)
    icd10_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("icd10_codes.id"), nullable=False)
    type: Mapped[DiagnosisType] = mapped_column(SAEnum(DiagnosisType), default=DiagnosisType.MAIN)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    encounter: Mapped["Encounter"] = relationship(back_populates="diagnoses")
    icd10: Mapped["ICD10Code"] = relationship()


class Prescription(Base):
    """Е-рецепт."""
    __tablename__ = "prescriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    encounter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("encounters.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    doctor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("doctors.id"), nullable=False)
    drug_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("drugs.id"), nullable=False)
    dosage: Mapped[str | None] = mapped_column(String(100))
    frequency: Mapped[str | None] = mapped_column(String(100))
    duration_days: Mapped[int | None] = mapped_column(SmallInteger)
    quantity: Mapped[int | None] = mapped_column(SmallInteger)
    instructions: Mapped[str | None] = mapped_column(Text)
    status: Mapped[PrescriptionStatus] = mapped_column(SAEnum(PrescriptionStatus), default=PrescriptionStatus.ACTIVE)

    # ЕСОЗ поля (заповнюються після відправки в Mock ЕСОЗ)
    esoz_request_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    esoz_request_number: Mapped[str | None] = mapped_column(String(50), index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    encounter: Mapped["Encounter"] = relationship(back_populates="prescriptions")
    patient: Mapped["Patient"] = relationship(back_populates="prescriptions")
    doctor: Mapped["Doctor"] = relationship()
    drug: Mapped["Drug"] = relationship()


class Referral(Base):
    """Е-направлення."""
    __tablename__ = "referrals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    encounter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("encounters.id"), nullable=False)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    doctor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("doctors.id"), nullable=False)
    specialization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("specializations.id"))
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ReferralStatus] = mapped_column(SAEnum(ReferralStatus), default=ReferralStatus.ACTIVE)
    esoz_referral_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    encounter: Mapped["Encounter"] = relationship(back_populates="referrals")
    patient: Mapped["Patient"] = relationship()
    doctor: Mapped["Doctor"] = relationship()
    specialization: Mapped["Specialization | None"] = relationship()


from app.models.patient import Patient        # noqa: E402
from app.models.doctor import Doctor          # noqa: E402
from app.models.reference import ICD10Code, Drug, Specialization  # noqa: E402
from app.models.scheduling import Appointment # noqa: E402
