"""
Unit tests for AdminService.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.doctor import Doctor
from app.models.scheduling import Schedule
from app.models.user import User, UserRole
from app.schemas.admin import UserAdminUpdate
from app.services.admin_service import AdminService
from tests.conftest import FakeRedis


def make_service(db: AsyncSession, redis: FakeRedis) -> AdminService:
    return AdminService(db=db, redis=redis)


async def _create_user(
    db: AsyncSession,
    email: str,
    role: UserRole,
) -> User:
    user = User(
        email=email,
        password_hash=hash_password("Pass12345!"),
        role=role,
        first_name="Тест",
        last_name="Користувач",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


class TestAdminUpdateUser:
    async def test_update_user_role_to_doctor_creates_doctor_profile(self, db_session, fake_redis):
        admin = await _create_user(db_session, "admin-role@test.com", UserRole.SUPER_ADMIN)
        target = await _create_user(db_session, "target@test.com", UserRole.PATIENT)
        svc = make_service(db_session, fake_redis)

        result = await svc.update_user(
            target.id,
            UserAdminUpdate(role=UserRole.DOCTOR),
            current_user=admin,
        )

        assert result.role == UserRole.DOCTOR
        doctor_profile = (await db_session.execute(
            select(Doctor).where(Doctor.user_id == target.id)
        )).scalar_one_or_none()
        assert doctor_profile is not None
        assert doctor_profile.is_active is True

        schedules = (await db_session.execute(
            select(Schedule).where(Schedule.doctor_id == doctor_profile.id, Schedule.is_active == True)
        )).scalars().all()
        assert len(schedules) == 5

