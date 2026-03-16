import random
import string
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ─── Password ────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# ─── JWT Tokens ──────────────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    """Raises JWTError if token is invalid or expired."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


# ─── 2FA OTP ─────────────────────────────────────────────────────────────────

def generate_otp(length: int = None) -> str:
    """Generate a numeric OTP code."""
    length = length or settings.OTP_LENGTH
    return "".join(random.choices(string.digits, k=length))


# ─── Redis OTP keys ──────────────────────────────────────────────────────────

def otp_redis_key(user_id: str) -> str:
    return f"otp:{user_id}"


def lockout_redis_key(user_id: str) -> str:
    return f"lockout:{user_id}"


def failed_attempts_key(user_id: str) -> str:
    return f"failed:{user_id}"


def refresh_token_blacklist_key(token_hash: str) -> str:
    return f"revoked_rt:{token_hash}"
