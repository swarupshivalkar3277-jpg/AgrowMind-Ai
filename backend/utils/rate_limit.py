from __future__ import annotations

from collections import defaultdict, deque
from time import monotonic

from fastapi import HTTPException, Request


_hits: dict[str, deque[float]] = defaultdict(deque)


def rate_limit(max_requests: int, window_seconds: int):
    async def limiter(request: Request) -> None:
        forwarded_for = request.headers.get("x-forwarded-for", "")
        client_ip = forwarded_for.split(",", 1)[0].strip()
        if not client_ip and request.client:
            client_ip = request.client.host
        key = f"{request.url.path}:{client_ip or 'unknown'}"

        now = monotonic()
        window_start = now - window_seconds
        bucket = _hits[key]
        while bucket and bucket[0] < window_start:
            bucket.popleft()

        if len(bucket) >= max_requests:
            raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")

        bucket.append(now)

    return limiter
