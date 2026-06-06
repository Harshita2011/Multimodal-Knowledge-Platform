from fastapi import UploadFile

from app.core.exceptions import AppError
from app.utils.files import sanitize_filename

ALLOWED_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx"}


def validate_upload(file: UploadFile, max_file_size_mb: int, payload_size: int) -> None:
    if not file.filename:
        raise AppError("missing_filename", "Filename is required", 400)
    if sanitize_filename(file.filename) != file.filename and ".." in file.filename:
        raise AppError("invalid_filename", "Filename contains unsafe path segments", 400)
    name = file.filename.lower()
    if file.content_type not in ALLOWED_TYPES and not any(name.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        raise AppError("invalid_mime", "Only PDF, DOCX, and PPTX uploads are supported", 415)
    if payload_size > max_file_size_mb * 1024 * 1024:
        raise AppError("file_too_large", f"Max file size is {max_file_size_mb}MB", 413)
    if payload_size < 5 or payload_size == 0:
        raise AppError("empty_file", "Uploaded file is empty", 400)
