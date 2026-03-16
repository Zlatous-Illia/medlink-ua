from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl
from typing import List


class Settings(BaseSettings):
    # ─── App ─────────────────────────────────────
    APP_NAME: str = "MedLink UA"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    # ─── Database ────────────────────────────────
    DATABASE_URL: str
    DATABASE_URL_SYNC: str

    # ─── Redis ───────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ─── JWT ─────────────────────────────────────
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ─── 2FA ─────────────────────────────────────
    OTP_EXPIRE_SECONDS: int = 300
    OTP_LENGTH: int = 6
    MAX_FAILED_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 15

    # ─── MinIO ───────────────────────────────────
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin123"
    MINIO_BUCKET_DOCUMENTS: str = "medlink-docs"
    MINIO_BUCKET_AVATARS: str = "medlink-avatars"
    MINIO_USE_SSL: bool = False

    # ─── Mock ЕСОЗ ───────────────────────────────
    ESOZ_MOCK_URL: str = "http://localhost:8080"
    ESOZ_CLIENT_ID: str = "medlink_mis_dev"
    ESOZ_CLIENT_SECRET: str = "mock_esoz_secret_2025"
    ESOZ_TOKEN_URL: str = "/api/oauth/tokens"

    # ─── Email ───────────────────────────────────
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_TLS: bool = True
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "noreply@medlink-ua.com"
    EMAIL_FROM_NAME: str = "MedLink UA"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
