from abc import ABC, abstractmethod


class OAuthProvider(ABC):
    @abstractmethod
    async def exchange_code(self, code: str, redirect_uri: str, nonce: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    async def get_identity(self, token_payload: dict) -> dict:
        raise NotImplementedError

    @abstractmethod
    def authorization_url(self, state: str, nonce: str, redirect_uri: str) -> str:
        raise NotImplementedError
