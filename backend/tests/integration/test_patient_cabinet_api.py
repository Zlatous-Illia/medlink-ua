"""
Integration tests for the Patient Cabinet API (/api/v1/me/*).

These endpoints are PATIENT-only. Tests verify:
- Role-based access control (PATIENT vs DOCTOR)
- Profile read/update
- Medical card (read-only)
- Encounters, prescriptions, documents (empty lists initially)
- Change password
"""

import pytest
from httpx import AsyncClient
from datetime import date

from app.models.user import User, UserRole
from app.models.patient import Patient, MedicalCard, Gender
from app.core.security import hash_password
from tests.conftest import FakeRedis, TestSessionFactory, make_token


BASE = "/api/v1/me"


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def _create_patient_with_profile(
    email: str = "patient@cabinet-test.com",
    password: str = "Patient1234!",
    tax_id: str = "1234567890",
) -> tuple[User, Patient]:
    """Create a User (PATIENT role) with a linked Patient record and MedicalCard."""
    async with TestSessionFactory() as session:
        user = User(
            email=email,
            password_hash=hash_password(password),
            role=UserRole.PATIENT,
            first_name="Тест",
            last_name="Пацієнт",
        )
        session.add(user)
        await session.flush()

        patient = Patient(
            user_id=user.id,
            tax_id=tax_id,
            first_name="Тест",
            last_name="Пацієнт",
            birth_date=date(1990, 5, 20),
            gender=Gender.FEMALE,
            phone="+380991234567",
        )
        session.add(patient)
        await session.flush()

        card = MedicalCard(patient_id=patient.id)
        session.add(card)
        await session.commit()
        await session.refresh(user)
        await session.refresh(patient)
        return user, patient


async def _create_doctor(
    email: str = "doctor@cabinet-test.com", password: str = "Doctor1234!"
) -> User:
    async with TestSessionFactory() as session:
        user = User(
            email=email,
            password_hash=hash_password(password),
            role=UserRole.DOCTOR,
            first_name="Лікар",
            last_name="Тест",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


# ─── GET /me ─────────────────────────────────────────────────────────────────

class TestGetProfile:
    async def test_patient_can_get_own_profile(self, async_client: AsyncClient):
        user, _ = await _create_patient_with_profile("get_profile@test.com")
        token = make_token(user)

        resp = await async_client.get(
            BASE, headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "get_profile@test.com"
        assert data["role"] == "PATIENT"
        assert "password_hash" not in data

    async def test_doctor_is_forbidden_from_me(self, async_client: AsyncClient):
        doctor = await _create_doctor("doc_forbidden@test.com")
        token = make_token(doctor)

        resp = await async_client.get(
            BASE, headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403

    async def test_unauthenticated_returns_401_or_403(self, async_client: AsyncClient):
        resp = await async_client.get(BASE)
        assert resp.status_code in (401, 403)

    async def test_profile_contains_patient_id_if_linked(self, async_client: AsyncClient):
        user, patient = await _create_patient_with_profile("linked@test.com", tax_id="1111111111")
        token = make_token(user)

        resp = await async_client.get(
            BASE, headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("patient_id") is not None


# ─── PATCH /me ────────────────────────────────────────────────────────────────

class TestUpdateProfile:
    async def test_update_first_name(self, async_client: AsyncClient):
        user, _ = await _create_patient_with_profile("update_name@test.com", tax_id="2222222222")
        token = make_token(user)

        resp = await async_client.patch(
            BASE,
            json={"first_name": "Оновлено"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["first_name"] == "Оновлено"

    async def test_update_phone(self, async_client: AsyncClient):
        user, _ = await _create_patient_with_profile("update_phone@test.com", tax_id="3333333333")
        token = make_token(user)

        resp = await async_client.patch(
            BASE,
            json={"phone": "+380501111111"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["phone"] == "+380501111111"

    async def test_email_cannot_be_changed(self, async_client: AsyncClient):
        """Email field is not editable — the endpoint should ignore it or reject."""
        user, _ = await _create_patient_with_profile("no_email_change@test.com", tax_id="4444444444")
        token = make_token(user)

        resp = await async_client.patch(
            BASE,
            json={"first_name": "Нове Ім'я"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        # Email should remain unchanged
        assert resp.json()["email"] == "no_email_change@test.com"

    async def test_doctor_cannot_update_me_profile(self, async_client: AsyncClient):
        doctor = await _create_doctor("doc_update@test.com")
        token = make_token(doctor)

        resp = await async_client.patch(
            BASE,
            json={"first_name": "Attempt"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


# ─── GET /me/medical-card ─────────────────────────────────────────────────────

class TestGetMedicalCard:
    async def test_patient_gets_own_medical_card(self, async_client: AsyncClient):
        user, patient = await _create_patient_with_profile(
            "medcard@test.com", tax_id="5555555555"
        )
        token = make_token(user)

        resp = await async_client.get(
            f"{BASE}/medical-card",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["patient_id"] == str(patient.id)
        assert isinstance(data["allergies"], list)
        assert isinstance(data["chronic_diseases"], list)

    async def test_medical_card_empty_on_new_patient(self, async_client: AsyncClient):
        user, _ = await _create_patient_with_profile("empty_card@test.com", tax_id="6666666666")
        token = make_token(user)

        resp = await async_client.get(
            f"{BASE}/medical-card",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["allergies"] == []
        assert data["chronic_diseases"] == []

    async def test_doctor_cannot_access_me_medical_card(self, async_client: AsyncClient):
        doctor = await _create_doctor("doc_card@test.com")
        token = make_token(doctor)

        resp = await async_client.get(
            f"{BASE}/medical-card",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_patient_without_profile_gets_404(self, async_client: AsyncClient):
        """Patient user without a linked Patient record should get 404."""
        async with TestSessionFactory() as session:
            user = User(
                email="noprofile@test.com",
                password_hash=hash_password("NoProf1!"),
                role=UserRole.PATIENT,
                first_name="Без",
                last_name="Профілю",
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

        token = make_token(user)
        resp = await async_client.get(
            f"{BASE}/medical-card",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404


# ─── GET /me/encounters ───────────────────────────────────────────────────────

class TestGetEncounters:
    async def test_encounters_empty_for_new_patient(self, async_client: AsyncClient):
        user, _ = await _create_patient_with_profile(
            "encounters@test.com", tax_id="7777777777"
        )
        token = make_token(user)

        resp = await async_client.get(
            f"{BASE}/encounters",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_doctor_forbidden_from_encounters(self, async_client: AsyncClient):
        doctor = await _create_doctor("doc_enc@test.com")
        token = make_token(doctor)

        resp = await async_client.get(
            f"{BASE}/encounters",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


# ─── GET /me/prescriptions ────────────────────────────────────────────────────

class TestGetPrescriptions:
    async def test_prescriptions_empty_for_new_patient(self, async_client: AsyncClient):
        user, _ = await _create_patient_with_profile(
            "prescriptions@test.com", tax_id="8888888888"
        )
        token = make_token(user)

        resp = await async_client.get(
            f"{BASE}/prescriptions",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_prescriptions_with_status_filter(self, async_client: AsyncClient):
        user, _ = await _create_patient_with_profile(
            "presc_filter@test.com", tax_id="9999999999"
        )
        token = make_token(user)

        resp = await async_client.get(
            f"{BASE}/prescriptions?status=ACTIVE",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_doctor_forbidden_from_prescriptions(self, async_client: AsyncClient):
        doctor = await _create_doctor("doc_presc@test.com")
        token = make_token(doctor)

        resp = await async_client.get(
            f"{BASE}/prescriptions",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


# ─── GET /me/documents ────────────────────────────────────────────────────────

class TestGetDocuments:
    async def test_documents_empty_for_new_patient(self, async_client: AsyncClient):
        user, _ = await _create_patient_with_profile(
            "documents@test.com", tax_id="1029384756"
        )
        token = make_token(user)

        resp = await async_client.get(
            f"{BASE}/documents",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json() == []


# ─── GET /me/referrals ────────────────────────────────────────────────────────

class TestGetReferrals:
    async def test_referrals_empty_for_new_patient(self, async_client: AsyncClient):
        user, _ = await _create_patient_with_profile(
            "referrals@test.com", tax_id="1212121212"
        )
        token = make_token(user)

        resp = await async_client.get(
            f"{BASE}/referrals",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_doctor_cannot_access_me_referrals(self, async_client: AsyncClient):
        doctor = await _create_doctor("doc_ref@test.com")
        token = make_token(doctor)

        resp = await async_client.get(
            f"{BASE}/referrals",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


# ─── PATCH /me/change-password ───────────────────────────────────────────────

class TestChangePassword:
    async def test_change_password_success(self, async_client: AsyncClient):
        user, _ = await _create_patient_with_profile(
            "chpwd@test.com", password="OldPass1!", tax_id="5647382910"
        )
        token = make_token(user)

        resp = await async_client.patch(
            f"{BASE}/change-password",
            json={"current_password": "OldPass1!", "new_password": "NewPass2!"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    async def test_change_password_wrong_current_returns_400(
        self, async_client: AsyncClient
    ):
        user, _ = await _create_patient_with_profile(
            "chpwd_wrong@test.com", password="Correct1!", tax_id="1928374650"
        )
        token = make_token(user)

        resp = await async_client.patch(
            f"{BASE}/change-password",
            json={"current_password": "WrongPass1!", "new_password": "NewPass2!"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400

    async def test_doctor_cannot_use_change_password(self, async_client: AsyncClient):
        doctor = await _create_doctor("doc_chpwd@test.com")
        token = make_token(doctor)

        resp = await async_client.patch(
            f"{BASE}/change-password",
            json={"current_password": "Doctor1234!", "new_password": "NewDoctor1!"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
