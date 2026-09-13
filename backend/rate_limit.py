# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

"""Minimal in-memory rate limiter for sensitive, unauthenticated endpoints
(login, register, forgot-password). Single-process fixed-window counter keyed
by client IP + route - resets on backend restart and doesn't share state
across multiple worker processes, but this app runs as a single uvicorn
process, so that's an acceptable trade-off for a self-hosted app of this size
versus pulling in Redis or a dedicated rate-limiting service."""

import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request

_buckets: dict[str, list[float]] = defaultdict(list)
_lock = Lock()


def rate_limiter(max_calls: int, period_seconds: int):
    def dependency(request: Request):
        client_ip = request.client.host if request.client else "unknown"
        key = f"{request.url.path}:{client_ip}"
        now = time.time()
        cutoff = now - period_seconds

        with _lock:
            timestamps = _buckets[key]
            while timestamps and timestamps[0] < cutoff:
                timestamps.pop(0)

            if len(timestamps) >= max_calls:
                raise HTTPException(
                    status_code=429,
                    detail="Zu viele Versuche. Bitte warte kurz und versuche es erneut."
                )

            timestamps.append(now)

    return dependency
