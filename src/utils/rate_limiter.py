"""Async token-bucket rate limiter for API calls"""

import asyncio
import time
from typing import Any


class AsyncRateLimiter:
    """Token bucket rate limiter"""

    def __init__(self, rate: float, period: float = 1.0, burst: int = 1):
        """
        Args:
            rate: Number of allowed requests per period
            period: Period duration in seconds
            burst: Maximum burst size
        """
        self._rate = rate
        self._period = period
        self._burst = burst
        self._tokens = float(burst)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Acquire a token, waiting if necessary"""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(self._burst, self._tokens + elapsed * self._rate / self._period)
            self._last_refill = now

            if self._tokens < 1.0:
                wait_time = (1.0 - self._tokens) * self._period / self._rate
                await asyncio.sleep(wait_time)
                self._tokens = 0.0
            else:
                self._tokens -= 1.0

    async def __aenter__(self) -> "AsyncRateLimiter":
        await self.acquire()
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass
