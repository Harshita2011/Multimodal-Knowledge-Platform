from abc import ABC, abstractmethod
from pathlib import Path

from app.core.exceptions import AppError
from app.utils.files import sanitize_filename


class DocumentStorage(ABC):
    @abstractmethod
    def save(self, file_bytes: bytes, filename: str, document_id: str) -> Path:
        raise NotImplementedError

    @abstractmethod
    def delete(self, path: Path) -> None:
        raise NotImplementedError


class LocalFileStorage(DocumentStorage):
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, file_bytes: bytes, filename: str, document_id: str) -> Path:
        safe = sanitize_filename(filename)
        target = self.base_dir / f"{document_id}_{safe}"
        target = target.resolve()
        if self.base_dir.resolve() not in target.parents:
            raise AppError("invalid_storage_path", "Resolved storage path is outside configured directory", 400)
        try:
            target.write_bytes(file_bytes)
        except Exception as exc:
            raise AppError("storage_write_failed", "Failed to persist uploaded file", 500) from exc
        return target

    def delete(self, path: Path) -> None:
        try:
            if path.exists():
                path.unlink()
        except Exception:
            pass
