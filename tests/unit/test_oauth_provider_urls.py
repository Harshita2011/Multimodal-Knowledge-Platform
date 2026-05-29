from app.auth.providers.google import GoogleOAuthProvider


def test_google_authorization_url_contains_state_and_nonce():
    provider = GoogleOAuthProvider()
    url = provider.authorization_url("st", "no", "http://localhost/callback")
    assert "state=st" in url
    assert "nonce=no" in url
