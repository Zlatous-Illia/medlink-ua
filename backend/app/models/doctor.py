import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, SmallInteger, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.user import utcnow


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)
    specialization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("specializations.id"))
    license_number: Mapped[str | None] = mapped_column(String(50))
    experience_years: Mapped[int | None] = mapped_column(SmallInteger)
    bio: Mapped[str | None] = mapped_column(Text)
    photo_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    user: Mapped["User"] = relationship()
    specialization: Mapped["Specialization | None"] = relationship()
    schedules: Mapped[list["Schedule"]] = relationship(back_populates="doctor", cascade="all, delete-orphan")
    appointments: Mapped[list["Appointment"]] = relationship(back_populates="doctor")
    encounters: Mapped[list["Encounter"]] = relationship(back_populates="doctor")

    @property
    def full_name(self) -> str:
        return self.user.full_name if self.user else ""


from app.models.user import User                           # noqa: E402
from app.models.reference import Specialization            # noqa: E402
from app.models.scheduling import Schedule, Appointment    # noqa: E402
from app.models.clinical import Encounter                  # noqa: E402
