
from app.auth.jwt import create_token, decode_token


def test_jwt_roundtrip():
    token = create_token({"sub": "u1", "email": "a@b.com"}, "secret", 10)
    payload = decode_token(token, "secret")
    assert payload["sub"] == "u1"
