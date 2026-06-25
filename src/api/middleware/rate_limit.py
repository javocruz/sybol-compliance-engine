import os
import time
from collections import defaultdict
from threading import Lock

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

# path prefix -> max requests per window
RATE_LIMITS: dict[str, tuple[int, int]] = {
    "/api/analyze": (10, 60),
    "/api/query": (30, 60),
    "/api/issue": (5, 60),
}

_store: dict[str, list[float]] = defaultdict(list)
_lock = Lock()


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _is_limited(path: str, key: str) -> tuple[bool, int]:
    for prefix, (limit, window) in RATE_LIMITS.items():
        if path == prefix or path.startswith(prefix + "/"):
            now = time.time()
            bucket = f"{prefix}:{key}"
            with _lock:
                hits = _store[bucket]
                hits[:] = [t for t in hits if now - t < window]
                if len(hits) >= limit:
                    retry_after = int(window - (now - hits[0])) + 1
                    return True, max(1, retry_after)
                hits.append(now)
            return False, 0
    return False, 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if os.getenv("DISABLE_RATE_LIMIT", "").lower() in ("1", "true", "yes"):
            return await call_next(request)
        limited, retry_after = _is_limited(request.url.path, _client_key(request))
        if limited:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)
