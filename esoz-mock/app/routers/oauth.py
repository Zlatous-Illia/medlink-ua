from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["OAuth"])

VALID_CLIENTS = {
    "medlink_mis_dev": "mock_esoz_secret_2025",
}


class TokenRequest(BaseModel):
    client_id: str
    client_secret: str
    grant_type: str = "client_credentials"


@router.post("/oauth/tokens")
async def get_token(data: TokenRequest):
    """OAuth2 Client Credentials — видача Bearer-токену МІС."""
    secret = VALID_CLIENTS.get(data.client_id)
    if not secret or secret != data.client_secret:
        raise HTTPException(status_code=401, detail="Invalid client credentials")

    return {
        "token_type": "Bearer",
        "access_token": f"mock_esoz_token_{data.client_id}_valid",
        "expires_in": 3600,
    }
