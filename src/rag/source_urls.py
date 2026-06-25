"""Map ingested regulation file paths to browser-safe API URLs."""

from pathlib import Path

REGULATIONS_API_PREFIX = "/api/regulations"


def resolve_source_url(
    source_path: str,
    regulation_type: str | None = None,
) -> str:
    """
    Convert a stored source_path (filesystem path or URL) into a link the UI can open.

    Ingested chunks store local PDF paths; the API serves those files under
    ``/api/regulations/{filename}``.
    """
    if source_path.startswith(("http://", "https://")):
        return source_path

    if source_path:
        name = Path(source_path).name
        if name.endswith(".pdf"):
            return f"{REGULATIONS_API_PREFIX}/{name}"

    if regulation_type:
        return f"{REGULATIONS_API_PREFIX}/{regulation_type}.pdf"

    return ""
