from typing import Any

from chromadb import PersistentClient


def build_chroma_client(path: str) -> Any:
    return PersistentClient(path=path)
