from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

import redis.asyncio as aioredis
from fastapi import HTTPException
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.clinical import Prescription, PrescriptionStatus, Encounter
from app.models.doctor import Doctor
from app.models.patient import Patient, Allergy
from app.models.reference import Drug
from app.models.user import AuditLog, User, UserRole
from app.schemas.prescriptions import (
    PrescriptionCreate, PrescriptionResponse, PrescriptionCancelRequest, DrugResponse,
)
from app.services.esoz_connector import esoz


class PrescriptionService:

    def __init__(self, db: AsyncSession, redis: aioredis.Redis):
        self.db = db
        self.redis = redis

    @staticmethod
    def _is_admin(user: User) -> bool:
        return user.role in (UserRole.ADMIN, UserRole.SUPER_ADMIN)

    async def _get_doctor_record(self, user: User, *, require_for_admin: bool = True) -> Optional[Doctor]:
        result = await self.db.execute(
            select(Doctor).where(Doctor.user_id == user.id)
        )
        doctor = result.scalar_one_or_none()
        if doctor:
            return doctor

        if self._is_admin(user) and not require_for_admin:
            # Admin/SuperAdmin can manage doctor resources without personal Doctor profile.
            return None

        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor profile not found")
        return doctor

    async def create_prescription(self, data: PrescriptionCreate, doctor_user: User) -> PrescriptionResponse:
        doctor = await self._get_doctor_record(doctor_user, require_for_admin=False)

        enc_result = await self.db.execute(
            select(Encounter).where(Encounter.id == data.encounter_id)
        )
        encounter = enc_result.scalar_one_or_none()
        if not encounter:
            raise HTTPException(status_code=404, detail="Encounter not found")
        if not self._is_admin(doctor_user) and (doctor is None or encounter.doctor_id != doctor.id):
            raise HTTPException(status_code=403, detail="Access denied")

        drug_result = await self.db.execute(
            select(Drug).where(Drug.id == data.drug_id)
        )
        drug = drug_result.scalar_one_or_none()
        if not drug:
            raise HTTPException(status_code=404, detail="Drug not found")

        dosage = data.dosage.strip()
        frequency = data.frequency.strip()
        instructions = data.instructions.strip()
        if not dosage or not frequency or not instructions:
            raise HTTPException(status_code=400, detail="All prescription fields must be filled")

        # ─── Allergy check ────────────────────────────────────────────────────
        if drug.inn:
            allergy_result = await self.db.execute(
                select(Allergy).where(Allergy.patient_id == encounter.patient_id)
            )
            allergies = allergy_result.scalars().all()
            drug_inn_lower = drug.inn.lower()
            for allergy in allergies:
                substance_lower = allergy.substance.lower()
                if substance_lower in drug_inn_lower or drug_inn_lower in substance_lower:
                    print(
                        f"[ALLERGY] Drug '{drug.inn}' conflicts with patient allergy "
                        f"'{allergy.substance}' (severity: {allergy.severity.value})"
                    )
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "warning": "Drug INN matches patient allergy",
                            "allergy": allergy.substance,
                            "drug_inn": drug.inn,
                            "severity": allergy.severity.value,
                        },
                    )

        prescription = Prescription(
            encounter_id=data.encounter_id,
            patient_id=encounter.patient_id,
            doctor_id=encounter.doctor_id,  # Use encounter's doctor, not actor's
            drug_id=data.drug_id,
            dosage=dosage,
            frequency=frequency,
            duration_days=data.duration_days,
            quantity=data.quantity,
            instructions=instructions,
            status=PrescriptionStatus.ACTIVE,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        self.db.add(prescription)
        await self.db.flush()

        try:
            payload = {
                "patient_id": str(prescription.patient_id),
                "doctor_id": str(encounter.doctor_id),
                "drug_inn": drug.inn,
                "atc_code": drug.atc_code,
                "dosage": data.dosage,
                "quantity": data.quantity,
                "created_at": prescription.created_at.isoformat(),
            }
            esoz_data = await esoz.create_prescription(payload)
            prescription.esoz_request_id = uuid.UUID(esoz_data["id"])
            prescription.esoz_request_number = esoz_data.get("request_number")
        except Exception:
            pass  # Continue even if ESOZ sync fails

        self.db.add(AuditLog(
            user_id=doctor_user.id, action="CREATE_PRESCRIPTION",
            resource="prescriptions", resource_id=prescription.id,
        ))
        await self.db.commit()

        result = await self.db.execute(
            select(Prescription)
            .where(Prescription.id == prescription.id)
            .options(selectinload(Prescription.drug))
        )
        prescription = result.scalar_one()
        return PrescriptionResponse.model_validate(prescription)

    async def get_prescription(self, prescription_id: uuid.UUID, requesting_user: User) -> PrescriptionResponse:
        result = await self.db.execute(
            select(Prescription)
            .where(Prescription.id == prescription_id)
            .options(selectinload(Prescription.drug))
        )
        prescription = result.scalar_one_or_none()
        if not prescription:
            raise HTTPException(status_code=404, detail="Prescription not found")

        if requesting_user.role == UserRole.PATIENT:
            patient_result = await self.db.execute(
                select(Patient).where(Patient.user_id == requesting_user.id)
            )
            patient = patient_result.scalar_one_or_none()
            if not patient or prescription.patient_id != patient.id:
                raise HTTPException(status_code=403, detail="Access denied")

        return PrescriptionResponse.model_validate(prescription)

    async def get_patient_prescriptions(self, patient_id: uuid.UUID, requesting_user: User) -> list[PrescriptionResponse]:
        if requesting_user.role == UserRole.PATIENT:
            patient_result = await self.db.execute(
                select(Patient).where(Patient.user_id == requesting_user.id)
            )
            patient = patient_result.scalar_one_or_none()
            if not patient or patient.id != patient_id:
                raise HTTPException(status_code=403, detail="Access denied")

        result = await self.db.execute(
            select(Prescription)
            .where(Prescription.patient_id == patient_id)
            .options(selectinload(Prescription.drug))
            .order_by(Prescription.created_at.desc())
        )
        prescriptions = result.scalars().all()
        return [PrescriptionResponse.model_validate(p) for p in prescriptions]

    async def cancel_prescription(self, prescription_id: uuid.UUID, data: PrescriptionCancelRequest, doctor_user: User) -> PrescriptionResponse:
        doctor = await self._get_doctor_record(doctor_user, require_for_admin=False)

        result = await self.db.execute(
            select(Prescription)
            .where(Prescription.id == prescription_id)
            .options(selectinload(Prescription.drug))
        )
        prescription = result.scalar_one_or_none()
        if not prescription:
            raise HTTPException(status_code=404, detail="Prescription not found")
        if not self._is_admin(doctor_user) and (doctor is None or prescription.doctor_id != doctor.id):
            raise HTTPException(status_code=403, detail="Access denied")
        if prescription.status != PrescriptionStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="Prescription is not active")

        if prescription.esoz_request_id:
            try:
                await esoz.cancel_prescription(str(prescription.esoz_request_id), data.reason)
            except Exception:
                pass

        prescription.status = PrescriptionStatus.CANCELLED
        self.db.add(AuditLog(
            user_id=doctor_user.id, action="CANCEL_PRESCRIPTION",
            resource="prescriptions", resource_id=prescription.id,
        ))
        await self.db.commit()
        await self.db.refresh(prescription)
        return PrescriptionResponse.model_validate(prescription)

    async def delete_prescription(self, prescription_id: uuid.UUID, doctor_user: User) -> None:
        doctor = await self._get_doctor_record(doctor_user, require_for_admin=False)

        result = await self.db.execute(
            select(Prescription).where(Prescription.id == prescription_id)
        )
        prescription = result.scalar_one_or_none()
        if not prescription:
            raise HTTPException(status_code=404, detail="Prescription not found")
        if not self._is_admin(doctor_user) and (doctor is None or prescription.doctor_id != doctor.id):
            raise HTTPException(status_code=403, detail="Access denied")

        await self.db.delete(prescription)
        self.db.add(AuditLog(
            user_id=doctor_user.id,
            action="DELETE_PRESCRIPTION",
            resource="prescriptions",
            resource_id=prescription_id,
        ))
        await self.db.commit()

    async def search_drugs(self, query: str, limit: int = 20) -> list[DrugResponse]:
        limit = min(limit, 50)
        normalized_query = (query or "").strip()
        statement = select(Drug).where(Drug.is_active == True)

        if normalized_query:
            pattern = f"%{normalized_query}%"
            statement = statement.where(
                or_(
                    Drug.inn.ilike(pattern),
                    Drug.trade_name.ilike(pattern),
                    Drug.atc_code.ilike(pattern),
                    Drug.form.ilike(pattern),
                    Drug.dosage.ilike(pattern),
                    Drug.manufacturer.ilike(pattern),
                )
            )

        result = await self.db.execute(statement.order_by(Drug.inn.asc()).limit(limit))
        drugs = result.scalars().all()
        return [DrugResponse.model_validate(d) for d in drugs]
