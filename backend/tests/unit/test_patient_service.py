"""
Unit tests for PatientService.

MinIO calls are mocked. DB uses medlink_test PostgreSQL.
Redis is FakeRedis.
"""

import uuid
import pytest
from datetime import date
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient import Patient, MedicalCard, Allergy, AllergySeverity
from app.models.user import User, UserRole
from app.core.security import hash_password
from app.schemas.patients import (
    PatientCreate, PatientUpdate,
    AllergyCreate, MedicalCardUpdate,
)
from app.services.patient_service import PatientService
from tests.conftest import FakeRedis


# ─── Helpers ─────────────────────────────────────────────────────────────────

def make_service(db: AsyncSession, redis: FakeRedis) -> PatientService:
    return PatientService(db=db, redis=redis)


async def _create_doctor(db: AsyncSession, email: str = "doctor@ps-test.com") -> User:
    user = User(
        email=email,
        password_hash=hash_password("Doctor1234!"),
        role=UserRole.DOCTOR,
        first_name="Лікар",
        last_name="Тестовий",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _create_patient_user(
    db: AsyncSession, email: str = "pat@ps-test.com"
) -> User:
    user = User(
        email=email,
        password_hash=hash_password("Patient1234!"),
        role=UserRole.PATIENT,
        first_name="Пацієнт",
        last_name="Тестовий",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def make_patient_create(tax_id: str = "1234567890") -> PatientCreate:
    return PatientCreate(
        tax_id=tax_id,
        first_name="Олена",
        last_name="Петренко",
        birth_date=date(1985, 6, 15),
        gender="FEMALE",
    )


# ─── Create patient ───────────────────────────────────────────────────────────

class TestCreatePatient:
    async def test_create_patient_success(self, db_session, fake_redis):
        doctor = await _create_doctor(db_session)
        svc = make_service(db_session, fake_redis)

        result = await svc.create_patient(make_patient_create(), created_by_user_id=doctor.id)

        assert result.tax_id == "1234567890"
        assert result.first_name == "Олена"
        assert result.is_active is True

    async def test_create_patient_also_creates_medical_card(self, db_session, fake_redis):
        doctor = await _create_doctor(db_session)
        svc = make_service(db_session, fake_redis)

        result = await svc.create_patient(make_patient_create("1111111111"), doctor.id)

        card = (await db_session.execute(
            select(MedicalCard).where(MedicalCard.patient_id == result.id)
        )).scalar_one_or_none()
        assert card is not None

    async def test_create_patient_duplicate_tax_id_raises_409(self, db_session, fake_redis):
        doctor = await _create_doctor(db_session)
        svc = make_service(db_session, fake_redis)

        await svc.create_patient(make_patient_create("2222222222"), doctor.id)

        with pytest.raises(HTTPException) as exc_info:
            await svc.create_patient(make_patient_create("2222222222"), doctor.id)
        assert exc_info.value.status_code == 409
        assert "tax_id" in exc_info.value.detail

    async def test_create_patient_with_optional_fields(self, db_session, fake_redis):
        doctor = await _create_doctor(db_session)
        svc = make_service(db_session, fake_redis)

        data = PatientCreate(
            tax_id="3333333333",
            first_name="Іван",
            last_name="Коваль",
            middle_name="Миколайович",
            birth_date=date(1990, 1, 1),
            gender="MALE",
            phone="+380501234567",
            email="ivan@example.com",
        )
        result = await svc.create_patient(data, doctor.id)
        assert result.phone == "+380501234567"
        assert result.email == "ivan@example.com"


# ─── Get patients (list) ─────────────────────────────────────────────────────

class TestGetPatients:
    async def test_get_patients_returns_all_active(self, db_session, fake_redis):
        doctor = await _create_doctor(db_session)
        svc = make_service(db_session, fake_redis)

        await svc.create_patient(make_patient_create("4444444444"), doctor.id)
        await svc.create_patient(make_patient_create("5555555555"), doctor.id)

        result = await svc.get_patients(search=None, skip=0, limit=10)
        assert len(result) == 2

    async def test_get_patients_search_by_last_name(self, db_session, fake_redis):
        doctor = await _create_doctor(db_session)
        svc = make_service(db_session, fake_redis)

        # Two patients with different last names
        data1 = PatientCreate(
            tax_id="6666666666",
            first_name="Марія",
            last_name="Шевченко",
            birth_date=date(1980, 3, 10),
            gender="FEMALE",
        )
        data2 = PatientCreate(
            tax_id="7777777777",
            first_name="Олег",
            last_name="Іваненко",
            birth_date=date(1975, 8, 22),
            gender="MALE",
        )
        await svc.create_patient(data1, doctor.id)
        await svc.create_patient(data2, doctor.id)

        result = await svc.get_patients(search="шевченко", skip=0, limit=10)
        assert len(result) == 1
        assert result[0].last_name == "Шевченко"

    async def test_get_patients_search_by_tax_id(self, db_session, fake_redis):
        doctor = await _create_doctor(db_session)
        svc = make_service(db_session, fake_redis)

        await svc.create_patient(make_patient_create("8888888888"), doctor.id)
        await svc.create_patient(make_patient_create("9999999999"), doctor.id)

        result = await svc.get_patients(search="8888", skip=0, limit=10)
        assert len(result) == 1
        assert result[0].tax_id == "8888888888"

    async def test_get_patients_pagination(self, db_session, fake_redis):
        doctor = await _create_doctor(db_session)
        svc = make_service(db_session, fake_redis)

        for i in range(5):
            await svc.create_patient(make_patient_create(f"00000000{i:02d}"), doctor.id)

        page1 = await svc.get_patients(search=None, skip=0, limit=3)
        page2 = await svc.get_patients(search=None, skip=3, limit=3)
        assert len(page1) == 3
        assert len(page2) == 2


# ─── Get single patient ───────────────────────────────────────────────────────

class TestGetPatient:
    async def test_doctor_can_get_any_patient(self, db_session, fake_redis):
        doctor = await _create_doctor(db_session)
        svc = make_service(db_session, fake_redis)

        created = await svc.create_patient(make_patient_create("1234509876"), doctor.id)
        result = await svc.get_patient(created.id, requesting_user=doctor)
        assert result.id == created.id

    async def test_patient_can_get_own_profile(self, db_session, fake_redis):
        doctor = await _create_doctor(db_session)
        patient_u = await _create_patient_user(db_session)
        svc = make_service(db_session, fake_redis)

        # Create patient and link to patient_user
        patient = await svc.create_patient(make_patient_create("5432109876"), doctor.id)

        # Manually link user_id
        p_row = (await db_session.execute(
            select(Patient).where(Patient.id == patient.id)
        )).scalar_one()
        p_row.user_id = patient_u.id
        await db_session.commit()

        result = await svc.get_patient(patient.id, requesting_user=patient_u)
        assert result.id == patient.id

    async def test_patient_cannot_get_other_patient(self, db_session, fake_redis):
        doctor = await _create_doctor(db_session)
        patient_u = await _create_patient_user(db_session, email="other@ps-test.com")
        svc = make_service(db_session, fake_redis)

        other_patient = await svc.create_patient(make_patient_create("1029384756"), doctor.id)

        with pytest.raises(HTTPException) as exc_info:
            await svc.get_patient(other_patient.id, requesting_user=patient_u)
        assert exc_info.value.status_code == 403

    async def test_get_nonexistent_patient_raises_404(self, db_session, fake_redis):
        doctor = await _create_doctor(db_session)
        svc = make_service(db_session, fake_redis)

        with pytest.raises(HTTPException) as exc_info:
            await svc.get_patient(uuid.uuid4(), requesting_user=doctor)
        assert exc_info.value.status_code == 404


# ─── Update patient ───────────────────────────────────────────────────────────

class TestUpdatePatient:
    async def test_update_patient_fields(self, db_session, fake_redis):
        doctor = await _create_doctor(db_session)
        svc = make_service(db_session, fake_redis)

        created = await svc.create_patient(make_patient_create("1122334455"), doctor.id)
        update_data = PatientUpdate(first_name="Оновлено", phone="+380661234567")

        result = await svc.update_patient(created.id, update_data, updated_by=doctor)
        assert result.first_name == "Оновлено"
        assert result.phone == "+380661234567"

    async def test_update_patient_partial_update(self, db_session, fake_redis):
        doctor = await _create_doctor(db_session)
        svc = make_service(db_session, fake_redis)

        created = await svc.create_patient(make_patient_create("9988776655"), doctor.id)
        # Update only phone, keep other fields
        result = await svc.update_patient(
            created.id, PatientUpdate(phone="+380501111111"), updated_by=doctor
        )
        assert result.phone == "+380501111111"
        assert result.last_name == "Петренко"  # unchanged


# ─── Allergies ────────────────────────────────────────────────────────────────

class TestAllergies:
    async def test_add_allergy_success(self, db_session, fake_redis):
        doctor = await _create_doctor(db_session)
        svc = make_service(db_session, fake_redis)

        patient = await svc.create_patient(make_patient_create("1357902468"), doctor.id)
        allergy_data = AllergyCreate(
            substance="Пеніцилін",
            severity=AllergySeverity.SEVERE,
            reaction="Анафілаксія",
        )
        result = await svc.add_allergy(patient.id, allergy_data)

        assert result.substance == "Пеніцилін"
        assert result.severity == AllergySeverity.SEVERE
        assert result.patient_id == patient.id

    async def test_add_allergy_persisted_in_db(self, db_session, fake_redis):
        doctor = await _create_doctor(db_session)
        svc = make_service(db_session, fake_redis)

        patient = await svc.create_patient(make_patient_create("2468013579"), doctor.id)
        await svc.add_allergy(
            patient.id, AllergyCreate(substance="Аспірин", severity=AllergySeverity.MILD)
        )

        allergies = (await db_session.execute(
            select(Allergy).where(Allergy.patient_id == patient.id)
        )).scalars().all()
        assert len(allergies) == 1
        assert allergies[0].substance == "Аспірин"

    async def test_add_multiple_allergies(self, db_session, fake_redis):
        doctor = await _create_doctor(db_session)
        svc = make_service(db_session, fake_redis)

        patient = await svc.create_patient(make_patient_create("1111222233"), doctor.id)
        await svc.add_allergy(
            patient.id, AllergyCreate(substance="Пеніцилін", severity=AllergySeverity.SEVERE)
        )
        await svc.add_allergy(
            patient.id, AllergyCreate(substance="Латекс", severity=AllergySeverity.MODERATE)
        )

        allergies = (await db_session.execute(
            select(Allergy).where(Allergy.patient_id == patient.id)
        )).scalars().all()
        assert len(allergies) == 2

    async def test_add_allergy_to_nonexistent_patient_raises_404(
        self, db_session, fake_redis
    ):
        svc = make_service(db_session, fake_redis)
        with pytest.raises(HTTPException) as exc_info:
            await svc.add_allergy(
                uuid.uuid4(),
                AllergyCreate(substance="X", severity=AllergySeverity.MILD),
            )
        assert exc_info.value.status_code == 404


# ─── Medical card ─────────────────────────────────────────────────────────────

class TestMedicalCard:
    async def test_get_medical_card_returns_card(self, db_session, fake_redis):
        doctor = await _create_doctor(db_session)
        svc = make_service(db_session, fake_redis)

        patient = await svc.create_patient(make_patient_create("3344556677"), doctor.id)
        card = await svc.get_medical_card(patient.id, requesting_user=doctor)

        assert card.patient_id == patient.id
        assert card.allergies == []
        assert card.chronic_diseases == []

    async def test_get_medical_card_includes_allergies(self, db_session, fake_redis):
        doctor = await _create_doctor(db_session)
        svc = make_service(db_session, fake_redis)

        patient = await svc.create_patient(make_patient_create("4455667788"), doctor.id)
        await svc.add_allergy(
            patient.id, AllergyCreate(substance="Котяча шерсть", severity=AllergySeverity.MILD)
        )

        card = await svc.get_medical_card(patient.id, requesting_user=doctor)
        assert len(card.allergies) == 1
        assert card.allergies[0].substance == "Котяча шерсть"

    async def test_update_medical_card_blood_type(self, db_session, fake_redis):
        doctor = await _create_doctor(db_session)
        svc = make_service(db_session, fake_redis)

        patient = await svc.create_patient(make_patient_create("5566778899"), doctor.id)

        from app.models.patient import BloodType
        update = MedicalCardUpdate(blood_type=BloodType.A_POS, height_cm=175, weight_kg=70.5)
        result = await svc.update_medical_card(patient.id, update, updated_by=doctor)

        assert result.blood_type == BloodType.A_POS
        assert result.height_cm == 175
        assert result.weight_kg == 70.5

    async def test_get_medical_card_for_nonexistent_patient_raises_404(
        self, db_session, fake_redis
    ):
        doctor = await _create_doctor(db_session)
        svc = make_service(db_session, fake_redis)

        with pytest.raises(HTTPException) as exc_info:
            await svc.get_medical_card(uuid.uuid4(), requesting_user=doctor)
        assert exc_info.value.status_code == 404
