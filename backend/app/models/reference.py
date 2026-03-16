import uuid
from sqlalchemy import String, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ICD10Code(Base):
    __tablename__ = "icd10_codes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    name_ua: Mapped[str] = mapped_column(Text, nullable=False)
    name_en: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(10))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self) -> str:
        return f"<ICD10 {self.code}: {self.name_ua[:40]}>"


class Drug(Base):
    __tablename__ = "drugs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    atc_code: Mapped[str | None] = mapped_column(String(10), index=True)        # АТХ-код
    inn: Mapped[str] = mapped_column(String(255), nullable=False, index=True)   # МНН (міжнародна назва)
    trade_name: Mapped[str | None] = mapped_column(String(255))                  # Торгова назва
    form: Mapped[str | None] = mapped_column(String(100))                        # таблетки, розчин...
    dosage: Mapped[str | None] = mapped_column(String(100))                      # 500 мг, 250 мг/5мл
    manufacturer: Mapped[str | None] = mapped_column(String(255))
    is_narcotic: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self) -> str:
        return f"<Drug {self.inn} [{self.atc_code}]>"


class Specialization(Base):
    __tablename__ = "specializations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name_ua: Mapped[str] = mapped_column(String(150), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(150))
    code: Mapped[str | None] = mapped_column(String(20), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
