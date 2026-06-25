"""Shared upload validation for analyze/issue routes."""

from fastapi import HTTPException, UploadFile

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
SUPPORTED_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})


async def read_validated_image(file: UploadFile) -> tuple[bytes, str | None, str | None]:
    if file.content_type not in SUPPORTED_TYPES:
        raise HTTPException(400, "Unsupported file type. Use JPEG, PNG, or WebP.")

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            413,
            f"File too large. Maximum size is {MAX_UPLOAD_BYTES // (1024 * 1024)}MB.",
        )
    if not content:
        raise HTTPException(400, "Empty file upload.")
    return content, file.filename, file.content_type
