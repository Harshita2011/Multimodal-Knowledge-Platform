import hashlib
import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres.models import OAuthStateModel, SessionModel, UserModel


class UserPgRepository:
    ANONYMOUS_USER_ID = "00000000-0000-0000-0000-000000000000"
    ANONYMOUS_USER_EMAIL = "anonymous@local.invalid"

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_email(self, email: str) -> UserModel | None:
        stmt = select(UserModel).where(UserModel.email == email)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_id(self, user_id: str) -> UserModel | None:
        return await self.session.get(UserModel, user_id)

    async def get_by_provider_identity(self, provider: str, provider_account_id: str) -> UserModel | None:
        stmt = select(UserModel).where(and_(UserModel.provider == provider, UserModel.provider_account_id == provider_account_id))
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create_user(
        self,
        *,
        email: str,
        name: str | None,
        provider: str | None,
        provider_account_id: str | None,
        password_hash: str | None,
        avatar_url: str | None = None,
    ) -> UserModel:
        user = UserModel(
            id=str(uuid.uuid4()),
            email=email,
            name=name,
            provider=provider,
            provider_account_id=provider_account_id,
            password_hash=password_hash,
            avatar_url=avatar_url,
            is_active=True,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def ensure_anonymous_user(self) -> UserModel:
        user = await self.session.get(UserModel, self.ANONYMOUS_USER_ID)
        if user is None:
            user = UserModel(
                id=self.ANONYMOUS_USER_ID,
                email=self.ANONYMOUS_USER_EMAIL,
                name="Anonymous",
                provider=None,
                provider_account_id=None,
                password_hash=None,
                avatar_url=None,
                is_active=True,
            )
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
        return user


class OAuthStateRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, provider: str, state: str, nonce: str, expires_at: datetime) -> OAuthStateModel:
        row = OAuthStateModel(
            id=str(uuid.uuid4()),
            provider=provider,
            state=state,
            nonce=nonce,
            expires_at=expires_at,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def consume_valid(self, provider: str, state: str) -> OAuthStateModel | None:
        now = datetime.now(timezone.utc)
        stmt = select(OAuthStateModel).where(
            and_(
                OAuthStateModel.provider == provider,
                OAuthStateModel.state == state,
                OAuthStateModel.consumed_at.is_(None),
                OAuthStateModel.expires_at > now,
            )
        )
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        row.consumed_at = now
        await self.session.commit()
        return row


class SessionPgRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    async def create(
        self,
        user_id: str,
        refresh_token: str,
        expires_at: datetime,
        user_agent: str | None = None,
        ip_address: str | None = None,
        device_name: str | None = None,
        family_id: str | None = None,
        parent_session_id: str | None = None,
    ) -> SessionModel:
        row = SessionModel(
            id=str(uuid.uuid4()),
            user_id=user_id,
            session_family_id=family_id or str(uuid.uuid4()),
            parent_session_id=parent_session_id,
            refresh_token_hash=self._hash_token(refresh_token),
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
            device_name=device_name,
            revoked=False,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def get_any_by_token(self, refresh_token: str) -> SessionModel | None:
        token_hash = self._hash_token(refresh_token)
        stmt = select(SessionModel).where(SessionModel.refresh_token_hash == token_hash)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_active_by_token(self, refresh_token: str) -> SessionModel | None:
        row = await self.get_any_by_token(refresh_token)
        if row is None:
            return None
        now = datetime.now(timezone.utc)
        if row.revoked or row.expires_at <= now:
            return None
        return row

    async def revoke(self, session_id: str, reason: str | None = None) -> None:
        row = await self.session.get(SessionModel, session_id)
        if row is not None:
            row.revoked = True
            row.revoked_reason = reason
            await self.session.commit()

    async def revoke_family(self, family_id: str, reason: str = "family_revoked") -> int:
        stmt = select(SessionModel).where(SessionModel.session_family_id == family_id)
        rows = list((await self.session.execute(stmt)).scalars().all())
        for r in rows:
            r.revoked = True
            r.revoked_reason = reason
        await self.session.commit()
        return len(rows)

    async def active_count_for_user(self, user_id: str) -> int:
        now = datetime.now(timezone.utc)
        stmt = select(SessionModel).where(
            and_(SessionModel.user_id == user_id, SessionModel.revoked.is_(False), SessionModel.expires_at > now)
        )
        return len(list((await self.session.execute(stmt)).scalars().all()))
