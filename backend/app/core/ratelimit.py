"""Per-client sliding-window limit on /api/*.
shortcut: in-process memory, so each worker counts separately; move to Redis when running more than one worker."""
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.config import settings

LIMIT = settings.rate_limit_per_min
WINDOW = 60.0
hits: dict[str, deque] = defaultdict(deque)


async def middleware(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        ip = request.client.host if request.client else "unknown"
        now, q = time.monotonic(), hits[ip]
        while q and now - q[0] > WINDOW:
            q.popleft()
        if len(q) >= LIMIT:
            return JSONResponse({"detail": "Too many requests. Please wait a minute."}, status_code=429)
        q.append(now)
    return await call_next(request)
