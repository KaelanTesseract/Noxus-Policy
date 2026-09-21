# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

"""In-memory rate limiting for unauthenticated, abuse-prone endpoints (login,
register, forgot/reset-password). Single-process sliding windows - state resets
on restart and isn't shared across worker processes, which is fine for this
app (one uvicorn process) versus pulling in Redis.

Client IP: request.client is the direct TCP peer. In this deployment that is
normally the Next.js server, not the browser, so *every* user would look like
the same IP - and if the real IP is taken from X-Forwarded-For naively, any
client can invent one (uvicorn's own proxy-header handling did exactly that,
so the limit was trivially bypassable). Set TRUSTED_PROXY_HOPS to the number
of reverse proxies you run in front (1 for a single Nginx Proxy Manager):
the client IP is then the entry that many positions from the right of
X-Forwarded-For, i.e. the one your own proxy appended, which a client can't
forge. With the default of 0, X-Forwarded-For is ignored entirely."""

import os
import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request

TRUSTED_PROXY_HOPS = int(os.getenv("TRUSTED_PROXY_HOPS", "0"))

_MAX_KEYS = 20000
_windows: dict[str, list[float]] = defaultdict(list)
_lock = Lock()


def get_client_ip(request: Request) -> str:
    peer = request.client.host if request.client else "unknown"
    if TRUSTED_PROXY_HOPS <= 0:
        return peer
    forwarded = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
    if len(forwarded) >= TRUSTED_PROXY_HOPS:
        return forwarded[-TRUSTED_PROXY_HOPS]
    return peer


def _recent(key: str, period_seconds: int, now: float) -> list[float]:
    stamps = _windows[key]
    cutoff = now - period_seconds
    while stamps and stamps[0] < cutoff:
        stamps.pop(0)
    return stamps


def _evict_if_needed(now: float, longest_period: int = 900):
    # Bound memory: random usernames/IPs would otherwise grow the table forever.
    if len(_windows) <= _MAX_KEYS:
        return
    for key in [k for k, v in _windows.items() if not v or v[-1] < now - longest_period]:
        del _windows[key]


def rate_limiter(max_calls: int, period_seconds: int):
    """FastAPI dependency: at most max_calls requests per client IP and route
    per period, counting every request."""
    def dependency(request: Request):
        key = f"calls:{request.url.path}:{get_client_ip(request)}"
        now = time.time()
        with _lock:
            stamps = _recent(key, period_seconds, now)
            if len(stamps) >= max_calls:
                raise HTTPException(
                    status_code=429,
                    detail="Zu viele Versuche. Bitte warte kurz und versuche es erneut."
                )
            stamps.append(now)
            _evict_if_needed(now)
    return dependency


class FailureLimiter:
    """Counts *failed* attempts only, per IP and per account name, so successful
    logins by other people never use up anyone's budget. The per-account limit
    is the real brute-force defence and doesn't depend on knowing the client IP;
    the per-IP limit slows password spraying across many accounts. Tradeoff: an
    attacker can lock a known account for the window by failing on purpose."""

    def __init__(self, name: str, ip_max: int, ip_period: int, account_max: int, account_period: int):
        self.name = name
        self.ip_max, self.ip_period = ip_max, ip_period
        self.account_max, self.account_period = account_max, account_period

    def _keys(self, request: Request, account: str):
        return (
            f"{self.name}:ip:{get_client_ip(request)}",
            f"{self.name}:acct:{(account or '').strip().lower()[:254]}",
        )

    def check(self, request: Request, account: str):
        ip_key, acct_key = self._keys(request, account)
        now = time.time()
        with _lock:
            blocked = (
                len(_recent(ip_key, self.ip_period, now)) >= self.ip_max
                or len(_recent(acct_key, self.account_period, now)) >= self.account_max
            )
        if blocked:
            raise HTTPException(
                status_code=429,
                detail="Zu viele fehlgeschlagene Versuche. Bitte warte einige Minuten und versuche es erneut."
            )

    def record_failure(self, request: Request, account: str):
        ip_key, acct_key = self._keys(request, account)
        now = time.time()
        with _lock:
            _recent(ip_key, self.ip_period, now).append(now)
            _recent(acct_key, self.account_period, now).append(now)
            _evict_if_needed(now)

    def reset_account(self, request: Request, account: str):
        _, acct_key = self._keys(request, account)
        with _lock:
            _windows.pop(acct_key, None)


login_failures = FailureLimiter(
    "login", ip_max=20, ip_period=300, account_max=10, account_period=900
)
