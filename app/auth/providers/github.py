import httpx
from urllib.parse import urlencode

from app.auth.providers.base import OAuthProvider
from app.core.settings import get_settings


class GitHubOAuthProvider(OAuthProvider):
    AUTH_URL = "https://github.com/login/oauth/authorize"
    TOKEN_URL = "https://github.com/login/oauth/access_token"
    USERINFO_URL = "https://api.github.com/user"
    EMAILS_URL = "https://api.github.com/user/emails"

    def __init__(self):
        self.settings = get_settings()

    def authorization_url(self, state: str, nonce: str, redirect_uri: str) -> str:
        params = {
            "client_id": self.settings.github_client_id,
            "redirect_uri": redirect_uri,
            "scope": "read:user user:email",
            "state": state,
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str, redirect_uri: str, nonce: str) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                self.TOKEN_URL,
                headers={"Accept": "application/json"},
                data={
                    "code": code,
                    "client_id": self.settings.github_client_id,
                    "client_secret": self.settings.github_client_secret,
                    "redirect_uri": redirect_uri,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            data["nonce"] = nonce
            return data

    async def get_identity(self, token_payload: dict) -> dict:
        access_token = token_payload.get("access_token", "")
        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
        async with httpx.AsyncClient(timeout=15) as client:
            user_resp = await client.get(self.USERINFO_URL, headers=headers)
            user_resp.raise_for_status()
            user = user_resp.json()
            email = user.get("email")
            if not email:
                emails_resp = await client.get(self.EMAILS_URL, headers=headers)
                emails_resp.raise_for_status()
                emails = emails_resp.json()
                primary = next((e for e in emails if e.get("primary")), None)
                email = (primary or {}).get("email", "")
        return {
            "provider": "github",
            "provider_account_id": str(user.get("id", "")),
            "email": str(email or ""),
            "name": user.get("name") or user.get("login"),
            "avatar_url": user.get("avatar_url"),
            "nonce": token_payload.get("nonce"),
        }
