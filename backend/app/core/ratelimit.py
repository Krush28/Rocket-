"""Per-client sliding-window limit on /api/*.
shortcut: in-process memory, so each worker counts separately; move to Redis when running more than one worker."""
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.config import settings

LIMIT = settings.rate_limit_per_min  # actions (POST): agent turns, orders, bookings
READ_LIMIT = int(__import__("os").getenv("RATE_LIMIT_READ_PER_MIN", "900"))  # screens polling (GET): bell, dashboard, journey, portals
WINDOW = 60.0
hits: dict[str, deque] = defaultdict(deque)


async def middleware(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        ip = request.client.host if request.client else "unknown"
        read = request.method == "GET"
        now, q = time.monotonic(), hits[("r:" if read else "w:") + ip]  # separate buckets: polling never starves a farmer's request
        while q and now - q[0] > WINDOW:
            q.popleft()
        if len(q) >= (READ_LIMIT if read else LIMIT):
            return JSONResponse({"detail": "Too many requests. Please wait a minute."}, status_code=429)
        q.append(now)
    return await call_next(request)
