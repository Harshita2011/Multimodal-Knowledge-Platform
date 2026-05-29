import asyncio

from app.auth.services import AuthService
from app.core.exceptions import AppError


class DummyUser:
    def __init__(self, user_id="u1", email="u@example.com"):
        self.id = user_id
        self.email = email


class DummyUserRepo:
    def __init__(self):
        self.user = DummyUser()

    async def get_by_email(self, email: str):
        return self.user

    async def get_by_id(self, user_id: str):
        return self.user

    async def get_by_provider_identity(self, provider: str, provider_account_id: str):
        return None

    async def create_user(self, **kwargs):
        return self.user


class DummySessionRow:
    def __init__(self):
        self.id = "s1"
        self.user_id = "u1"
        self.session_family_id = "f1"


class DummySessionRepo:
    async def get_any_by_token(self, refresh_token: str):
        return DummySessionRow()

    async def get_active_by_token(self, refresh_token: str):
        return None

    async def revoke_family(self, family_id: str, reason: str = "family_revoked"):
        return 2

    async def active_count_for_user(self, user_id: str):
        return 0


class DummyOAuthStateRepo:
    async def create(self, **kwargs):
        return None

    async def consume_valid(self, provider: str, state: str):
        return None


def test_refresh_replay_detected_revokes_family():
    svc = AuthService(DummyUserRepo(), DummySessionRepo(), DummyOAuthStateRepo())
    try:
        asyncio.run(svc.refresh("old_refresh"))
    except AppError as exc:
        assert exc.code == "refresh_replay_detected"
        return
    raise AssertionError("Expected refresh replay detection")
