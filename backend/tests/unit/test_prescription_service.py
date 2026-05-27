"""
Unit tests for PrescriptionService.
"""

import uuid
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.clinical import Encounter, EncounterStatus, Prescription, PrescriptionStatus
from app.models.doctor import Doctor
from app.models.patient import Patient, MedicalCard, Allergy, AllergySeverity, Gender
from app.models.reference import Drug
from app.models.user import User, UserRole
from app.schemas.prescriptions import PrescriptionCreate
from app.services.prescription_service import PrescriptionService
from tests.conftest import FakeRedis


def make_service(db: AsyncSession, redis: FakeRedis) -> PrescriptionService:
    return PrescriptionService(db=db, redis=redis)


async def _create_doctor(db: AsyncSession, email: str = "doctor@rx-test.com") -> tuple[User, Doctor]:
    user = User(
        email=email,
        password_hash=hash_password("Doctor1234!"),
        role=UserRole.DOCTOR,
        first_name="Лікар",
        last_name="Тестовий",
    )
    db.add(user)
    await db.flush()
    doctor = Doctor(user_id=user.id, is_active=True)
    db.add(doctor)
    await db.commit()
    await db.refresh(user)
    await db.refresh(doctor)
    return user, doctor


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


async def _create_encounter(db: AsyncSession, patient: Patient, doctor: Doctor) -> Encounter:
    encounter = Encounter(
        patient_id=patient.id,
        doctor_id=doctor.id,
        status=EncounterStatus.IN_PROGRESS,
    )
    db.add(encounter)
    await db.commit()
    await db.refresh(encounter)
    return encounter


class TestDrugSearch:
    async def test_search_drugs_returns_all_on_empty_query(self, db_session, fake_redis):
        await _create_doctor(db_session)
        svc = make_service(db_session, fake_redis)
        db_session.add_all([
            Drug(inn="Amoxicillin", trade_name="Amoxiclav", form="Tablets", dosage="500 mg", manufacturer="Sandoz", is_active=True),
            Drug(inn="Paracetamol", trade_name="Panadol", form="Syrup", dosage="250 mg/5ml", manufacturer="GSK", is_active=True),
            Drug(inn="Inactive", trade_name="Inactive", form="Form", dosage="Dose", manufacturer="Maker", is_active=False),
        ])
        await db_session.commit()

        result = await svc.search_drugs("")
        assert len(result) == 2
        assert {item.inn for item in result} == {"Amoxicillin", "Paracetamol"}

    async def test_search_drugs_matches_additional_fields(self, db_session, fake_redis):
        await _create_doctor(db_session, email="doctor2@rx-test.com")
        svc = make_service(db_session, fake_redis)
        db_session.add(Drug(
            inn="Ibuprofen",
            trade_name="Nurofen",
            form="Film-coated tablets",
            dosage="200 mg",
            manufacturer="Reckitt",
            is_active=True,
        ))
        await db_session.commit()

        result = await svc.search_drugs("reckitt")
        assert len(result) == 1
        assert result[0].inn == "Ibuprofen"


class TestAllergyWarning:
    async def test_create_prescription_raises_409_on_allergy_match(self, db_session, fake_redis):
        doctor_user, doctor = await _create_doctor(db_session, email="doctor3@rx-test.com")
        patient = await _create_patient(db_session, tax_id="2222222222")
        encounter = await _create_encounter(db_session, patient, doctor)
        svc = make_service(db_session, fake_redis)

        db_session.add(Allergy(patient_id=patient.id, substance="Amoxicillin", severity=AllergySeverity.SEVERE))
        drug = Drug(inn="Amoxicillin", trade_name="Amoxil", is_active=True)
        db_session.add(drug)
        await db_session.commit()

        with patch("app.services.esoz_connector.esoz.create_prescription", new=AsyncMock()) as _patched:
            with pytest.raises(HTTPException) as exc_info:
                await svc.create_prescription(
                    PrescriptionCreate(
                        encounter_id=encounter.id,
                        drug_id=drug.id,
                        dosage="500 mg",
                        frequency="twice daily",
                        duration_days=7,
                        quantity=14,
                        instructions="After meal",
                    ),
                    doctor_user,
                )

        assert exc_info.value.status_code == 409
        assert exc_info.value.detail == {
            "warning": "Drug INN matches patient allergy",
            "allergy": "Amoxicillin",
            "drug_inn": "Amoxicillin",
            "severity": "SEVERE",
        }
        assert (await db_session.execute(select(Encounter).where(Encounter.id == encounter.id))).scalar_one().status == EncounterStatus.IN_PROGRESS

    async def test_create_prescription_succeeds_when_no_allergy_match(self, db_session, fake_redis):
        doctor_user, doctor = await _create_doctor(db_session, email="doctor4@rx-test.com")
        patient = await _create_patient(db_session, tax_id="3333333333")
        encounter = await _create_encounter(db_session, patient, doctor)
        svc = make_service(db_session, fake_redis)

        db_session.add(Drug(inn="Paracetamol", trade_name="Panadol", is_active=True))
        await db_session.commit()
        drug = (await db_session.execute(select(Drug).where(Drug.inn == "Paracetamol"))).scalar_one()

        with patch(
            "app.services.esoz_connector.esoz.create_prescription",
            new=AsyncMock(return_value={"id": str(uuid.uuid4()), "request_number": "REQ-001"}),
        ):
            result = await svc.create_prescription(
                PrescriptionCreate(
                    encounter_id=encounter.id,
                    drug_id=drug.id,
                    dosage="500 mg",
                    frequency="once daily",
                    duration_days=5,
                    quantity=5,
                    instructions="Before sleep",
                ),
                doctor_user,
            )

        assert result.status == PrescriptionStatus.ACTIVE
        assert result.drug is not None
        assert result.drug.inn == "Paracetamol"
        assert result.esoz_request_number == "REQ-001"

    async def test_delete_prescription_removes_row(self, db_session, fake_redis):
        doctor_user, doctor = await _create_doctor(db_session, email="doctor5@rx-test.com")
        patient = await _create_patient(db_session, tax_id="4444444444")
        encounter = await _create_encounter(db_session, patient, doctor)
        svc = make_service(db_session, fake_redis)

        db_session.add(Drug(inn="Ibuprofen", trade_name="Nurofen", is_active=True))
        await db_session.commit()
        drug = (await db_session.execute(select(Drug).where(Drug.inn == "Ibuprofen"))).scalar_one()

        with patch(
            "app.services.esoz_connector.esoz.create_prescription",
            new=AsyncMock(return_value={"id": str(uuid.uuid4()), "request_number": "REQ-DELETE"}),
        ):
            created = await svc.create_prescription(
                PrescriptionCreate(
                    encounter_id=encounter.id,
                    drug_id=drug.id,
                    dosage="200 mg",
                    frequency="twice daily",
                    duration_days=3,
                    quantity=6,
                    instructions="After food",
                ),
                doctor_user,
            )

        await svc.delete_prescription(created.id, doctor_user)
        deleted = await db_session.get(Prescription, created.id)
        assert deleted is None

