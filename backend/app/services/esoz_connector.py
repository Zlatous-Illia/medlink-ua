"""
ЕСОЗ Connector — клієнт для взаємодії з Mock ЕСОЗ API.

У продакшені замінити ESOZ_MOCK_URL на реальний URL ЦБД ЕСОЗ.
Інтерфейс залишається незмінним.
"""
import uuid
from typing import Optional
import httpx
from app.core.config import settings


class ESOZConnector:
    """HTTP client for ЕСОЗ API (Mock or Real)."""

    def __init__(self):
        self.base_url = settings.ESOZ_MOCK_URL
        self.client_id = settings.ESOZ_CLIENT_ID
        self.client_secret = settings.ESOZ_CLIENT_SECRET
        self._token: Optional[str] = None

    async def _get_token(self) -> str:
        """Obtain OAuth2 Bearer token from ЕСОЗ."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/oauth/tokens",
                json={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "client_credentials",
                },
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["access_token"]

    async def _headers(self) -> dict:
        token = await self._get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    # ─── Patients ────────────────────────────────────────────────────────────

    async def verify_person(self, tax_id: str) -> dict:
        """Verify patient by РНОКПП (tax_id) in ЕСОЗ registry."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/api/persons",
                params={"tax_id": tax_id},
                headers=await self._headers(),
                timeout=10.0,
            )
            resp.raise_for_status()
            return resp.json()

    # ─── Prescriptions ───────────────────────────────────────────────────────

    async def create_prescription(self, payload: dict) -> dict:
        """Send e-prescription to ЕСОЗ. Returns {id, request_number, status}."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/medication_requests",
                json=payload,
                headers=await self._headers(),
                timeout=15.0,
            )
            resp.raise_for_status()
            return resp.json().get("data", {})

    async def cancel_prescription(self, esoz_request_id: str, reason: str) -> dict:
        """Cancel e-prescription in ЕСОЗ."""
        async with httpx.AsyncClient() as client:
            resp = await client.patch(
                f"{self.base_url}/api/medication_requests/{esoz_request_id}",
                json={"status": "cancelled", "cancel_reason": reason},
                headers=await self._headers(),
                timeout=10.0,
            )
            resp.raise_for_status()
            return resp.json().get("data", {})

    async def get_prescription(self, esoz_request_id: str) -> dict:
        """Get prescription status from ЕСОЗ."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/api/medication_requests/{esoz_request_id}",
                headers=await self._headers(),
                timeout=10.0,
            )
            resp.raise_for_status()
            return resp.json().get("data", {})

    # ─── Referrals ───────────────────────────────────────────────────────────

    async def create_referral(self, payload: dict) -> dict:
        """Send e-referral to ЕСОЗ."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/referrals",
                json=payload,
                headers=await self._headers(),
                timeout=10.0,
            )
            resp.raise_for_status()
            return resp.json().get("data", {})

    # ─── Drugs directory ─────────────────────────────────────────────────────

    async def get_drugs(self, query: str = "", limit: int = 20) -> list:
        """Search drugs in ЕСОЗ (АТХ/МНН directory)."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/api/innm_dosages",
                params={"name": query, "page_size": limit},
                headers=await self._headers(),
                timeout=10.0,
            )
            resp.raise_for_status()
            return resp.json().get("data", [])


# Singleton instance
esoz = ESOZConnector()
