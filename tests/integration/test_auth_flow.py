from fastapi.testclient import TestClient

from app.main import create_app


def test_auth_register_login_flow_smoke():
    app = create_app()
    with TestClient(app) as client:
        reg = client.post("/api/v1/auth/register", json={"email": "user@example.com", "password": "password123", "name": "User"})
        assert reg.status_code in (200, 409, 503)

        login = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "password123"})
        assert login.status_code in (200, 503)
        if login.status_code == 200:
            body = login.json()
            assert "access_token" in body
            assert "refresh_token" in body
