from app.auth.providers.github import GitHubOAuthProvider
from app.auth.providers.google import GoogleOAuthProvider


def get_provider(provider: str):
    if provider == "google":
        return GoogleOAuthProvider()
    if provider == "github":
        return GitHubOAuthProvider()
    raise ValueError(f"Unsupported provider: {provider}")
