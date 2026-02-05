"""Tests for AsyncRateLimiter"""

import asyncio
import time

import pytest

from src.utils.rate_limiter import AsyncRateLimiter


class TestAsyncRateLimiter:
    """Test suite for AsyncRateLimiter"""

    @pytest.mark.asyncio
    async def test_allows_burst_requests(self):
        """Burst requests should pass immediately"""
        limiter = AsyncRateLimiter(rate=10, period=1.0, burst=3)
        start = time.monotonic()
        for _ in range(3):
            await limiter.acquire()
        elapsed = time.monotonic() - start
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_blocks_after_burst(self):
        """Requests after burst should be delayed"""
        limiter = AsyncRateLimiter(rate=10, period=1.0, burst=1)
        await limiter.acquire()  # Use the one burst token
        start = time.monotonic()
        await limiter.acquire()  # Should wait
        elapsed = time.monotonic() - start
        assert elapsed >= 0.05  # Should have some delay

    @pytest.mark.asyncio
    async def test_refills_tokens_over_time(self):
        """Tokens should refill after waiting"""
        limiter = AsyncRateLimiter(rate=100, period=1.0, burst=1)
        await limiter.acquire()  # Use token
        await asyncio.sleep(0.05)  # Wait for refill
        start = time.monotonic()
        await limiter.acquire()  # Should be quick now
        elapsed = time.monotonic() - start
        assert elapsed < 0.05

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Should work as async context manager"""
        limiter = AsyncRateLimiter(rate=10, period=1.0, burst=1)
        async with limiter:
            pass  # Should not raise

    @pytest.mark.asyncio
    async def test_concurrent_access(self):
        """Multiple concurrent acquisitions should be safe"""
        limiter = AsyncRateLimiter(rate=100, period=1.0, burst=5)

        async def acquire_token():
            await limiter.acquire()

        tasks = [acquire_token() for _ in range(5)]
        await asyncio.gather(*tasks)

    @pytest.mark.asyncio
    async def test_respects_rate(self):
        """Rate parameter should control throughput"""
        limiter = AsyncRateLimiter(rate=50, period=1.0, burst=1)
        await limiter.acquire()
        start = time.monotonic()
        await limiter.acquire()
        elapsed = time.monotonic() - start
        # At 50/sec, each token takes 0.02s
        assert elapsed >= 0.01

    @pytest.mark.asyncio
    async def test_respects_period(self):
        """Period parameter should be respected"""
        limiter = AsyncRateLimiter(rate=1, period=0.1, burst=1)
        await limiter.acquire()
        start = time.monotonic()
        await limiter.acquire()
        elapsed = time.monotonic() - start
        assert elapsed >= 0.05

    @pytest.mark.asyncio
    async def test_zero_burst_waits(self):
        """With burst=0, first acquire should wait"""
        limiter = AsyncRateLimiter(rate=100, period=1.0, burst=0)
        start = time.monotonic()
        await limiter.acquire()
        elapsed = time.monotonic() - start
        assert elapsed >= 0.005
