from urllib.parse import urlencode

import httpx

from app.auth.providers.base import OAuthProvider
from app.core.settings import get_settings


class GoogleOAuthProvider(OAuthProvider):
    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

    def __init__(self):
        self.settings = get_settings()

    def authorization_url(self, state: str, nonce: str, redirect_uri: str) -> str:
        params = {
            "client_id": self.settings.google_client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "nonce": nonce,
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str, redirect_uri: str, nonce: str) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                self.TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self.settings.google_client_id,
                    "client_secret": self.settings.google_client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            resp.raise_for_status()
            data = dict(resp.json())
            data["nonce"] = nonce
            return data

    async def get_identity(self, token_payload: dict) -> dict:
        access_token = token_payload.get("access_token", "")
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(self.USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"})
            resp.raise_for_status()
            info = resp.json()
        return {
            "provider": "google",
            "provider_account_id": str(info.get("sub", "")),
            "email": str(info.get("email", "")),
            "name": info.get("name"),
            "avatar_url": info.get("picture"),
            "nonce": token_payload.get("nonce"),
        }
