from chromadb import PersistentClient


def build_chroma_client(path: str) -> PersistentClient:
    return PersistentClient(path=path)
