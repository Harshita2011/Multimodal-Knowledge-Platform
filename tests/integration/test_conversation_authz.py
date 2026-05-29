from fastapi.testclient import TestClient

from app.main import create_app


def test_conversation_routes_require_auth():
    app = create_app()
    client = TestClient(app)
    resp = client.get("/api/v1/conversations")
    assert resp.status_code == 401
