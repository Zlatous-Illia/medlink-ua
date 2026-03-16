from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1 import auth

# Import all models so SQLAlchemy knows about them
import app.models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"🏥 {settings.APP_NAME} v{settings.APP_VERSION} starting...")
    yield
    # Shutdown
    await engine.dispose()
    print("👋 Shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Електронна медична інформаційна система (ЕМІС) — Backend API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ─── CORS ────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ─────────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/api/v1")

# TODO Week 2+: add more routers as modules are built
# app.include_router(patients.router, prefix="/api/v1")
# app.include_router(encounters.router, prefix="/api/v1")
# app.include_router(prescriptions.router, prefix="/api/v1")
# app.include_router(appointments.router, prefix="/api/v1")
# app.include_router(analytics.router, prefix="/api/v1")


@app.get("/", tags=["Health"])
async def root():
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
