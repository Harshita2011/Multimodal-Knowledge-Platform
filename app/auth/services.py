import secrets
from datetime import datetime, timedelta, timezone

from app.auth.jwt import create_token
from app.auth.passwords import hash_password, verify_password
from app.auth.providers import get_provider
from app.auth.schemas import AuthTokens, LoginRequest, RegisterRequest, UserMe
from app.core.exceptions import AppError
from app.core.settings import get_settings
from app.core.telemetry import TelemetryEvent, emit
from app.db.postgres.repositories.auth_repo import OAuthStateRepository, SessionPgRepository, UserPgRepository
from app.security.audit import audit


class AuthService:
    def __init__(
        self,
        user_repo: UserPgRepository,
        session_repo: SessionPgRepository,
        oauth_state_repo: OAuthStateRepository,
    ):
        self.user_repo = user_repo
        self.session_repo = session_repo
        self.oauth_state_repo = oauth_state_repo
        self.settings = get_settings()

    async def register(self, req: RegisterRequest, ip_address: str | None = None) -> UserMe:
        existing = await self.user_repo.get_by_email(req.email)
        if existing is not None:
            raise AppError("email_in_use", "Email already registered", 409)
        user = await self.user_repo.create_user(
            email=req.email,
            name=req.name,
            provider=None,
            provider_account_id=None,
            password_hash=hash_password(req.password),
        )
        audit("user_registered", user_id=user.id, email=user.email, ip_address=ip_address)
        return UserMe(id=user.id, email=user.email, name=user.name, provider=user.provider, provider_account_id=user.provider_account_id)

    async def login(self, req: LoginRequest, user_agent: str | None = None, ip_address: str | None = None, device_name: str | None = None) -> AuthTokens:
        user = await self.user_repo.get_by_email(req.email)
        if user is None or not user.password_hash or not verify_password(req.password, user.password_hash):
            raise AppError("invalid_credentials", "Invalid email or password", 401)
        audit("user_logged_in", user_id=user.id, email=user.email, ip_address=ip_address)
        tokens = await self._issue_tokens(user.id, user.email, user_agent=user_agent, ip_address=ip_address, device_name=device_name)
        active_sessions = await self.session_repo.active_count_for_user(user.id)
        emit(TelemetryEvent(name="auth.password_login", attrs={"password_logins": 1, "active_sessions": active_sessions}))
        return tokens

    async def create_oauth_authorization(self, provider: str, redirect_uri: str) -> dict:
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=self.settings.oauth_state_ttl_minutes)
        await self.oauth_state_repo.create(provider=provider, state=state, nonce=nonce, expires_at=expires_at)
        auth_url = get_provider(provider).authorization_url(state=state, nonce=nonce, redirect_uri=redirect_uri)
        return {"provider": provider, "authorization_url": auth_url, "state": state}

    async def oauth_callback(
        self,
        provider: str,
        code: str,
        state: str,
        redirect_uri: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
        device_name: str | None = None,
    ) -> AuthTokens:
        state_row = await self.oauth_state_repo.consume_valid(provider=provider, state=state)
        if state_row is None:
            audit("oauth_state_invalid", provider=provider, state=state)
            raise AppError("invalid_oauth_state", "Invalid or expired OAuth state", 401)

        provider_client = get_provider(provider)
        token_payload = await provider_client.exchange_code(code=code, redirect_uri=redirect_uri, nonce=state_row.nonce)
        identity = await provider_client.get_identity(token_payload)

        if identity.get("nonce") != state_row.nonce:
            audit("oauth_nonce_invalid", provider=provider, state=state)
            raise AppError("invalid_oauth_nonce", "OAuth nonce mismatch", 401)

        provider_account_id = str(identity.get("provider_account_id", ""))
        email = str(identity.get("email", "")).lower()
        if not provider_account_id or not email:
            raise AppError("oauth_identity_invalid", "OAuth identity missing required fields", 401)

        user = await self.user_repo.get_by_provider_identity(provider, provider_account_id)
        if user is None:
            linked = await self.user_repo.get_by_email(email)
            if linked is None:
                user = await self.user_repo.create_user(
                    email=email,
                    name=identity.get("name"),
                    provider=provider,
                    provider_account_id=provider_account_id,
                    password_hash=None,
                    avatar_url=identity.get("avatar_url"),
                )
            else:
                linked.provider = provider
                linked.provider_account_id = provider_account_id
                linked.avatar_url = identity.get("avatar_url")
                user = linked
                await self.user_repo.session.commit()

        audit("oauth_login", user_id=user.id, provider=provider, ip_address=ip_address)
        tokens = await self._issue_tokens(user.id, user.email, user_agent=user_agent, ip_address=ip_address, device_name=device_name)
        active_sessions = await self.session_repo.active_count_for_user(user.id)
        emit(TelemetryEvent(name="auth.oauth_login", attrs={"oauth_logins": 1, "active_sessions": active_sessions}))
        return tokens

    async def refresh(
        self,
        refresh_token: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
        device_name: str | None = None,
    ) -> AuthTokens:
        any_row = await self.session_repo.get_any_by_token(refresh_token)
        if any_row is None:
            raise AppError("invalid_refresh", "Refresh token invalid", 401)

        active_row = await self.session_repo.get_active_by_token(refresh_token)
        if active_row is None:
            revoked_count = await self.session_repo.revoke_family(any_row.session_family_id, reason="refresh_replay_detected")
            audit("refresh_replay_detected", user_id=any_row.user_id, family_id=any_row.session_family_id, revoked_count=revoked_count)
            emit(TelemetryEvent(name="auth.refresh_replay", attrs={"refresh_replays_detected": 1, "session_family_revocations": 1}))
            raise AppError("refresh_replay_detected", "Refresh replay detected; session family revoked", 401)

        await self.session_repo.revoke(active_row.id, reason="rotated")
        user = await self.user_repo.get_by_id(active_row.user_id)
        if user is None:
            raise AppError("unauthorized", "User not found", 401)
        emit(TelemetryEvent(name="auth.refresh_rotated", attrs={"refresh_rotations": 1}))
        audit("refresh_rotated", user_id=user.id, family_id=active_row.session_family_id)
        tokens = await self._issue_tokens(
            user.id,
            user.email,
            user_agent=user_agent,
            ip_address=ip_address,
            device_name=device_name,
            family_id=active_row.session_family_id,
            parent_session_id=active_row.id,
        )
        active_sessions = await self.session_repo.active_count_for_user(user.id)
        emit(TelemetryEvent(name="auth.active_sessions", attrs={"active_sessions": active_sessions}))
        return tokens

    async def logout(self, refresh_token: str) -> None:
        row = await self.session_repo.get_any_by_token(refresh_token)
        if row is not None:
            await self.session_repo.revoke(row.id, reason="logout")
            audit("logout", user_id=row.user_id, session_id=row.id)
            emit(TelemetryEvent(name="auth.logout", attrs={"session_revoked": 1}))

    async def _issue_tokens(
        self,
        user_id: str,
        email: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
        device_name: str | None = None,
        family_id: str | None = None,
        parent_session_id: str | None = None,
    ) -> AuthTokens:
        access = create_token({"sub": user_id, "email": email}, self.settings.jwt_secret_key, self.settings.jwt_access_token_minutes)
        refresh_raw = secrets.token_urlsafe(48)
        refresh = create_token({"sub": user_id, "jti": refresh_raw}, self.settings.jwt_secret_key, self.settings.jwt_refresh_token_minutes)
        await self.session_repo.create(
            user_id=user_id,
            refresh_token=refresh,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=self.settings.jwt_refresh_token_minutes),
            user_agent=user_agent,
            ip_address=ip_address,
            device_name=device_name,
            family_id=family_id,
            parent_session_id=parent_session_id,
        )
        return AuthTokens(access_token=access, refresh_token=refresh)
