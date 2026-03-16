"""
Mock ЕСОЗ Server
================
Імітує REST API ЦБД ЕСОЗ відповідно до технічних вимог НСЗУ.
Використовується для розробки та дипломної демонстрації.

Запуск: uvicorn app.main:app --reload --port 8080
Swagger: http://localhost:8080/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import oauth, prescriptions, persons, drugs, referrals

app = FastAPI(
    title="Mock ЕСОЗ API",
    description="Імітація ЦБД ЕСОЗ (eHealth) для розробки МІС. Відповідає реальному API НСЗУ.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(oauth.router,         prefix="/api")
app.include_router(persons.router,       prefix="/api")
app.include_router(prescriptions.router, prefix="/api")
app.include_router(drugs.router,         prefix="/api")
app.include_router(referrals.router,     prefix="/api")


@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "Mock ЕСОЗ API",
        "status": "running",
        "note": "This is a mock server for development. Not a real ЕСОЗ endpoint.",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
