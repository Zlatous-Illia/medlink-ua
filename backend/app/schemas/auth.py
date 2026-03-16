from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
import uuid
from datetime import datetime
from app.models.user import UserRole


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    role: UserRole = UserRole.PATIENT

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class OTPVerifyRequest(BaseModel):
    email: EmailStr
    otp_code: str = Field(min_length=6, max_length=6)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: UserRole
    first_name: str
    last_name: str
    middle_name: Optional[str]
    phone: Optional[str]
    avatar_url: Optional[str]
    is_active: bool
    is_2fa_enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginStep1Response(BaseModel):
    """Returned after successful password check — awaiting OTP."""
    message: str = "OTP sent to your email"
    email: str
    requires_2fa: bool = True
