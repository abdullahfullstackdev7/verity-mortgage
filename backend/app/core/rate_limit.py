"""In-memory login rate limiting: slows down brute-force attempts against a
single account without punishing unrelated concurrent users behind the
same IP (a shared office NAT, for example).

Keyed by (client IP, email) so it targets repeated failures against one
account, and only failed attempts count -- a burst of successful logins
never trips it. State is per-process (no Redis dependency), which is a
real limitation across multiple worker processes/instances; documented in
the security checklist rather than silently assumed away.
"""

from __future__ import annotations

import time
from collections import defaultdict

WINDOW_SECONDS = 300  # 5 minutes
MAX_FAILED_ATTEMPTS = 5

_failed_attempts: dict[tuple[str, str], list[float]] = defaultdict(list)


class RateLimitExceeded(Exception):
    def __init__(self, retry_after_seconds: int):
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"Too many attempts; retry after {retry_after_seconds}s")


def _key(ip: str, email: str) -> tuple[str, str]:
    return (ip, email.strip().lower())


def _prune(attempts: list[float], now: float) -> None:
    cutoff = now - WINDOW_SECONDS
    while attempts and attempts[0] < cutoff:
        attempts.pop(0)


def check_login_rate_limit(ip: str, email: str) -> None:
    now = time.time()
    attempts = _failed_attempts[_key(ip, email)]
    _prune(attempts, now)
    if len(attempts) >= MAX_FAILED_ATTEMPTS:
        retry_after = int(WINDOW_SECONDS - (now - attempts[0])) + 1
        raise RateLimitExceeded(max(retry_after, 1))


def record_failed_login(ip: str, email: str) -> None:
    _failed_attempts[_key(ip, email)].append(time.time())


def reset_login_attempts(ip: str, email: str) -> None:
    _failed_attempts.pop(_key(ip, email), None)
