"""
Integration tests to verify admin has all doctor capabilities.
This tests the requirement: "Администратор должен обладать всеми возможностями доктора"
"""

import pytest
import uuid
from httpx import AsyncClient
from tests.conftest import FakeRedis


@pytest.mark.asyncio
async def test_admin_can_list_doctors_without_trailing_slash(async_client: AsyncClient, fake_redis: FakeRedis):
    """Admin should be able to access doctors list endpoint without trailing slash."""
    admin_token = await _create_user_and_login(
        async_client, fake_redis, "admin@test.com", "Admin@123456", role="ADMIN"
    )

    response = await async_client.get(
        "/api/v1/doctors",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_admin_can_view_medical_card(async_client: AsyncClient, fake_redis: FakeRedis):
    """Admin should be able to view patient medical card without doctor profile."""
    # Create admin user (no doctor profile)
    admin_token = await _create_user_and_login(
        async_client, fake_redis, "admin@test.com", "Admin@123456", role="ADMIN"
    )

    # Create doctor for patient
    doctor_token = await _create_user_and_login(
        async_client, fake_redis, "doctor@test.com", "Doctor@123456", role="DOCTOR"
    )

    # Create patient
    patient_response = await async_client.post(
        "/api/v1/patients",
        json={
            "first_name": "John",
            "last_name": "Doe",
            "tax_id": "1234567890",
            "gender": "MALE",
            "birth_date": "1990-01-01",
            "phone": "+380123456789",
        },
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert patient_response.status_code == 201, f"Expected 201, got {patient_response.status_code}: {patient_response.text}"
    patient_id = patient_response.json()["id"]

    # Admin should be able to view medical card
    medical_card_response = await async_client.get(
        f"/api/v1/patients/{patient_id}/medical-card",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert medical_card_response.status_code == 200, f"Expected 200, got {medical_card_response.status_code}: {medical_card_response.text}"


@pytest.mark.asyncio
async def test_admin_can_add_allergy(async_client: AsyncClient, fake_redis: FakeRedis):
    """Admin should be able to add patient allergy."""
    admin_token = await _create_user_and_login(
        async_client, fake_redis, "admin@test.com", "Admin@123456", role="ADMIN"
    )

    doctor_token = await _create_user_and_login(
        async_client, fake_redis, "doctor@test.com", "Doctor@123456", role="DOCTOR"
    )

    # Create patient
    patient_response = await async_client.post(
        "/api/v1/patients",
        json={
            "first_name": "John",
            "last_name": "Doe",
            "tax_id": "1234567890",
            "gender": "MALE",
            "birth_date": "1990-01-01",
            "phone": "+380123456789",
        },
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    patient_id = patient_response.json()["id"]

    # Admin adds allergy
    allergy_response = await async_client.post(
        f"/api/v1/patients/{patient_id}/allergies",
        json={
            "substance": "Penicillin",
            "severity": "SEVERE",
            "notes": "Severe reaction",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert allergy_response.status_code == 201, f"Expected 201, got {allergy_response.status_code}: {allergy_response.text}"


@pytest.mark.asyncio
async def test_admin_can_delete_encounter(async_client: AsyncClient, fake_redis: FakeRedis):
    """Admin should be able to delete encounter without doctor profile."""
    admin_token = await _create_user_and_login(
        async_client, fake_redis, "admin@test.com", "Admin@123456", role="ADMIN"
    )

    doctor_token = await _create_user_and_login(
        async_client, fake_redis, "doctor@test.com", "Doctor@123456", role="DOCTOR"
    )

    # Create patient
    patient_response = await async_client.post(
        "/api/v1/patients",
        json={
            "first_name": "John",
            "last_name": "Doe",
            "tax_id": "1234567890",
            "gender": "MALE",
            "birth_date": "1990-01-01",
            "phone": "+380123456789",
        },
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    patient_id = patient_response.json()["id"]

    # Doctor creates encounter
    encounter_response = await async_client.post(
        "/api/v1/encounters",
        json={
            "patient_id": str(patient_id),
            "appointment_id": None,
            "complaints": "Headache",
        },
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert encounter_response.status_code == 201
    encounter_id = encounter_response.json()["id"]

    # Admin deletes encounter
    delete_response = await async_client.delete(
        f"/api/v1/encounters/{encounter_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert delete_response.status_code == 204, f"Expected 204, got {delete_response.status_code}: {delete_response.text}"

    # Verify encounter is deleted
    get_response = await async_client.get(
        f"/api/v1/encounters/{encounter_id}",
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_admin_can_create_prescription(async_client: AsyncClient, fake_redis: FakeRedis):
    """Admin should be able to create prescription without doctor profile."""
    admin_token = await _create_user_and_login(
        async_client, fake_redis, "admin@test.com", "Admin@123456", role="ADMIN"
    )

    doctor_token = await _create_user_and_login(
        async_client, fake_redis, "doctor@test.com", "Doctor@123456", role="DOCTOR"
    )

    # Create patient
    patient_response = await async_client.post(
        "/api/v1/patients",
        json={
            "first_name": "John",
            "last_name": "Doe",
            "tax_id": "1234567890",
            "gender": "MALE",
            "birth_date": "1990-01-01",
            "phone": "+380123456789",
        },
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    patient_id = patient_response.json()["id"]

    # Doctor creates encounter
    encounter_response = await async_client.post(
        "/api/v1/encounters",
        json={
            "patient_id": str(patient_id),
            "appointment_id": None,
            "complaints": "Headache",
        },
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    encounter_id = encounter_response.json()["id"]

    # Get a drug ID (assuming drugs exist in DB)
    drugs_response = await async_client.get(
        "/api/v1/prescriptions/drugs/search?q=a&limit=1",
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    if drugs_response.status_code == 200 and drugs_response.json():
        drug_id = drugs_response.json()[0]["id"]

        # Admin creates prescription
        rx_response = await async_client.post(
            "/api/v1/prescriptions",
            json={
                "encounter_id": str(encounter_id),
                "drug_id": str(drug_id),
                "dosage": "500mg",
                "frequency": "twice daily",
                "duration_days": 10,
                "quantity": 20,
                "instructions": "After meals",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert rx_response.status_code in [201, 409], f"Expected 201 or 409, got {rx_response.status_code}: {rx_response.text}"


async def _create_user_and_login(async_client: AsyncClient, fake_redis: FakeRedis, email: str, password: str, role: str = "PATIENT") -> str:
    """Helper: create user and perform full 2FA login, return access token."""
    # Register
    register_response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "role": role,
            "first_name": "Test",
            "last_name": "User",
        },
    )
    assert register_response.status_code == 201
    user_id = register_response.json()["id"]

    # Login step 1
    login_response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200

    # Get OTP from fake redis
    otp = fake_redis._store.get(f"otp:{user_id}")
    assert otp is not None, f"OTP not found for user {user_id}"

    # Login step 2 (2FA)
    twofa_response = await async_client.post(
        "/api/v1/auth/login/2fa",
        json={"email": email, "otp_code": otp},
    )
    assert twofa_response.status_code == 200, f"Expected 200, got {twofa_response.status_code}: {twofa_response.text}"
    return twofa_response.json()["access_token"]


@pytest.mark.asyncio
async def test_super_admin_can_view_medical_card(async_client: AsyncClient, fake_redis: FakeRedis):
    """Verify SUPER_ADMIN also has all doctor capabilities."""
    # Create super admin
    super_admin_token = await _create_user_and_login(
        async_client, fake_redis, "superadmin@test.com", "SuperAdmin@123456", role="SUPER_ADMIN"
    )

    # Create doctor for patient
    doctor_token = await _create_user_and_login(
        async_client, fake_redis, "doctor@test.com", "Doctor@123456", role="DOCTOR"
    )

    # Create patient
    patient_response = await async_client.post(
        "/api/v1/patients",
        json={
            "first_name": "John",
            "last_name": "Doe",
            "tax_id": "1234567890",
            "gender": "MALE",
            "birth_date": "1990-01-01",
            "phone": "+380123456789",
        },
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    assert patient_response.status_code == 201
    patient_id = patient_response.json()["id"]

    # SUPER_ADMIN should be able to view medical card
    medical_card_response = await async_client.get(
        f"/api/v1/patients/{patient_id}/medical-card",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )
    assert medical_card_response.status_code == 200


