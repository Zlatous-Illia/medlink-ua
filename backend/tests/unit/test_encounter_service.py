"""
Unit tests for EncounterService referral/encounter lifecycle operations.
"""

from datetime import date
from unittest.mock import AsyncMock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.clinical import Encounter, Diagnosis, Referral, ReferralStatus, EncounterStatus
from app.models.doctor import Doctor
from app.models.patient import Patient, MedicalCard, Gender
from app.models.reference import ICD10Code
from app.models.user import User, UserRole
from app.schemas.encounters import EncounterCreate, EncounterUpdate, ReferralCreate, ReferralUpdate
from app.services.encounter_service import EncounterService
from tests.conftest import FakeRedis


def make_service(db: AsyncSession, redis: FakeRedis) -> EncounterService:
    return EncounterService(db=db, redis=redis)


async def _create_doctor(db: AsyncSession, email: str = "doctor@enc-test.com") -> User:
    user = User(
        email=email,
        password_hash=hash_password("Doctor1234!"),
        role=UserRole.DOCTOR,
        first_name="Лікар",
        last_name="Тестовий",
    )
    db.add(user)
    await db.flush()
    db.add(Doctor(user_id=user.id, is_active=True))
    await db.commit()
    await db.refresh(user)
    return user


async def _create_patient(db: AsyncSession, tax_id: str = "1234567890") -> Patient:
    patient = Patient(
        tax_id=tax_id,
        first_name="Пацієнт",
        last_name="Тестовий",
        birth_date=date(1990, 1, 1),
        gender=Gender.MALE,
    )
    db.add(patient)
    await db.flush()
    db.add(MedicalCard(patient_id=patient.id))
    await db.commit()
    await db.refresh(patient)
    return patient


async def _create_encounter(db: AsyncSession, doctor_user: User, patient: Patient) -> Encounter:
    svc = make_service(db, FakeRedis())
    result = await svc.create_encounter(EncounterCreate(patient_id=patient.id), doctor_user)
    return await db.get(Encounter, result.id)


class TestEncounterLifecycle:
    async def test_update_and_cancel_encounter(self, db_session, fake_redis):
        doctor = await _create_doctor(db_session)
        patient = await _create_patient(db_session)
        svc = make_service(db_session, fake_redis)

        encounter = await _create_encounter(db_session, doctor, patient)
        updated = await svc.update_encounter(
            encounter.id,
            EncounterUpdate(complaints="Головний біль", recommendations="Пиття та відпочинок"),
            doctor,
        )
        assert updated.complaints == "Головний біль"
        assert updated.recommendations == "Пиття та відпочинок"

        cancelled = await svc.cancel_encounter(encounter.id, doctor)
        assert cancelled.status == EncounterStatus.CANCELLED


    async def test_delete_encounter_removes_rows(self, db_session, fake_redis):
        doctor = await _create_doctor(db_session, email="doctor3@enc-test.com")
        patient = await _create_patient(db_session, tax_id="3333333333")
        svc = make_service(db_session, fake_redis)

        encounter = await _create_encounter(db_session, doctor, patient)
        icd10 = ICD10Code(code="B00", name_ua="Герпесвірусні інфекції", is_active=True)
        db_session.add(icd10)
        await db_session.commit()

        from app.schemas.encounters import DiagnosisCreate
        await svc.add_diagnosis(encounter.id, DiagnosisCreate(icd10_id=icd10.id), doctor)

        with patch("app.services.esoz_connector.esoz.create_referral", new=AsyncMock(return_value={"id": "ref-1"})):
            referral = await svc.create_referral(
                ReferralCreate(encounter_id=encounter.id, reason="Додаткове обстеження"),
                doctor,
            )

        await svc.delete_encounter(encounter.id, doctor)

        assert await db_session.get(Encounter, encounter.id) is None
        assert not (await db_session.execute(select(Diagnosis).where(Diagnosis.encounter_id == encounter.id))).scalars().all()
        assert not (await db_session.execute(select(Referral).where(Referral.encounter_id == encounter.id))).scalars().all()


class TestReferralLifecycle:
    async def test_update_cancel_delete_referral(self, db_session, fake_redis):
        doctor = await _create_doctor(db_session, email="doctor4@enc-test.com")
        patient = await _create_patient(db_session, tax_id="4444444444")
        svc = make_service(db_session, fake_redis)
        encounter = await _create_encounter(db_session, doctor, patient)

        with patch("app.services.esoz_connector.esoz.create_referral", new=AsyncMock(return_value={"id": "ref-2"})):
            referral = await svc.create_referral(
                ReferralCreate(encounter_id=encounter.id, reason="Консультація"),
                doctor,
            )

        updated = await svc.update_referral(referral.id, ReferralUpdate(reason="Оновлена причина"), doctor)
        assert updated.reason == "Оновлена причина"

        cancelled = await svc.cancel_referral(referral.id, doctor)
        assert cancelled.status == ReferralStatus.CANCELLED

        await svc.delete_referral(referral.id, doctor)
        assert await db_session.get(Referral, referral.id) is None


class TestICD10Search:
    async def test_search_icd10_returns_all_on_empty_query(self, db_session, fake_redis):
        doctor = await _create_doctor(db_session, email="doctor5@enc-test.com")
        svc = make_service(db_session, fake_redis)

        db_session.add_all([
            ICD10Code(code="A01", name_ua="Черевний тиф", name_en="Typhoid fever", is_active=True),
            ICD10Code(code="B02", name_ua="Опоясувальний герпес", name_en="Zoster [herpes zoster]", is_active=True),
            ICD10Code(code="C03", name_ua="Inactive code", name_en="Inactive", is_active=False),
        ])
        await db_session.commit()

        result = await svc.search_icd10("")
        assert len(result) == 2
        assert {item.code for item in result} == {"A01", "B02"}

    async def test_search_icd10_matches_english_name(self, db_session, fake_redis):
        doctor = await _create_doctor(db_session, email="doctor6@enc-test.com")
        svc = make_service(db_session, fake_redis)

        db_session.add(ICD10Code(code="D10", name_ua="Доброякісні новоутворення", name_en="Benign neoplasms", is_active=True))
        await db_session.commit()

        result = await svc.search_icd10("benign")
        assert len(result) == 1
        assert result[0].code == "D10"


