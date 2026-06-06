from urllib.parse import quote

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import UserContext, get_current_user
from app.auth.schemas import AuthTokens, LoginRequest, RefreshRequest, RegisterRequest, UserMe
from app.auth.services import AuthService
from app.core.exceptions import AppError
from app.core.settings import get_settings
from app.db.postgres.repositories.auth_repo import OAuthStateRepository, SessionPgRepository, UserPgRepository
from app.db.postgres.session import get_db_session, get_db_unavailable_message
from app.security.rate_limiter import limiter

router = APIRouter(prefix="/auth", tags=["auth"])


def _svc(session: AsyncSession) -> AuthService:
    if session is None:
        raise AppError("db_unavailable", get_db_unavailable_message("auth operations"), 503)
    return AuthService(UserPgRepository(session), SessionPgRepository(session), OAuthStateRepository(session))


def _ip(request: Request) -> str:
    return request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")


@router.post("/register", response_model=UserMe)
async def register(req: RegisterRequest, request: Request, session: AsyncSession = Depends(get_db_session)):
    if not limiter.allow(f"auth:register:{_ip(request)}", limit=5, window_seconds=60):
        raise AppError("rate_limited", "Too many register attempts", 429)
    return await _svc(session).register(req, ip_address=_ip(request))


@router.post("/login", response_model=AuthTokens)
async def login(req: LoginRequest, request: Request, user_agent: str | None = Header(default=None), session: AsyncSession = Depends(get_db_session)):
    if not limiter.allow(f"auth:login:{_ip(request)}", limit=10, window_seconds=60):
        raise AppError("rate_limited", "Too many login attempts", 429)
    return await _svc(session).login(req, user_agent=user_agent, ip_address=_ip(request), device_name=user_agent)


@router.post("/refresh", response_model=AuthTokens)
async def refresh(req: RefreshRequest, request: Request, user_agent: str | None = Header(default=None), session: AsyncSession = Depends(get_db_session)):
    key = f"auth:refresh:{_ip(request)}"
    if not limiter.allow(key, limit=30, window_seconds=60):
        raise AppError("rate_limited", "Too many refresh attempts", 429)
    return await _svc(session).refresh(req.refresh_token, user_agent=user_agent, ip_address=_ip(request), device_name=user_agent)


@router.post("/logout")
async def logout(req: RefreshRequest, session: AsyncSession = Depends(get_db_session)):
    await _svc(session).logout(req.refresh_token)
    return {"ok": True}


@router.get("/me", response_model=UserMe)
async def me(user: UserContext = Depends(get_current_user), session: AsyncSession = Depends(get_db_session)):
    repo = UserPgRepository(session)
    row = await repo.get_by_email(user.email)
    return UserMe(id=row.id, email=row.email, name=row.name, provider=row.provider, provider_account_id=row.provider_account_id)


@router.get("/google")
async def google_entry(session: AsyncSession = Depends(get_db_session)):
    redirect_uri = "http://localhost:8000/api/v1/auth/google/callback"
    return await _svc(session).create_oauth_authorization(
        "google",
        redirect_uri=redirect_uri
    )

@router.get("/github")
async def github_entry(session: AsyncSession = Depends(get_db_session)):
    settings = get_settings()
    redirect_uri = f"{settings.api_prefix}/auth/github/callback"
    return await _svc(session).create_oauth_authorization("github", redirect_uri=redirect_uri)


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str,
    request: Request,
    user_agent: str | None = Header(default=None),
    session: AsyncSession = Depends(get_db_session),
):
    redirect_uri = "http://localhost:8000/api/v1/auth/google/callback"

    tokens = await _svc(session).oauth_callback(
        provider="google",
        code=code,
        state=state,
        redirect_uri=redirect_uri,
        user_agent=user_agent,
        ip_address=_ip(request),
        device_name=user_agent,
    )

    frontend_url = (
        f"http://localhost:3000/auth/callback"
        f"?access_token={quote(tokens.access_token)}"
        f"&refresh_token={quote(tokens.refresh_token)}"
    )

    return RedirectResponse(url=frontend_url)



@router.get("/github/callback", response_model=AuthTokens)
async def github_callback(code: str, state: str, request: Request, user_agent: str | None = Header(default=None), session: AsyncSession = Depends(get_db_session)):
    settings = get_settings()
    redirect_uri = f"{settings.api_prefix}/auth/github/callback"
    return await _svc(session).oauth_callback(
        provider="github",
        code=code,
        state=state,
        redirect_uri=redirect_uri,
        user_agent=user_agent,
        ip_address=_ip(request),
        device_name=user_agent,
    )
