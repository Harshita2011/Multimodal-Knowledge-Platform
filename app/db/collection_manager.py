from app.db.repositories.vector_repository import VectorRepository


class CollectionManager:
    def __init__(self, repo: VectorRepository):
        self.repo = repo

    def ensure_initialized(self) -> None:
        self.repo.initialize_collection()
