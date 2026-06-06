from datetime import UTC, datetime, timedelta

import jwt


def create_token(payload: dict, secret: str, expires_minutes: int) -> str:
    now = datetime.now(UTC)
    to_encode = payload | {"iat": int(now.timestamp()), "exp": int((now + timedelta(minutes=expires_minutes)).timestamp())}
    return jwt.encode(to_encode, secret, algorithm="HS256")


def decode_token(token: str, secret: str) -> dict:
    return jwt.decode(token, secret, algorithms=["HS256"])
