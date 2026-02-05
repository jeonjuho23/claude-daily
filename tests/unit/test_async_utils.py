"""
Unit tests for src/utils/async_utils.py
"""

import asyncio
from unittest.mock import Mock, patch

import pytest

from src.utils.async_utils import create_background_task


class TestCreateBackgroundTask:
    """Tests for create_background_task function"""

    @pytest.mark.asyncio
    async def test_creates_task(self):
        """Should create an asyncio.Task"""

        async def sample_coro():
            return "done"

        task = create_background_task(sample_coro())
        assert isinstance(task, asyncio.Task)

        # Clean up
        result = await task
        assert result == "done"

    @pytest.mark.asyncio
    async def test_task_executes_coroutine(self):
        """Task should execute the coroutine"""
        result_holder = []

        async def sample_coro():
            result_holder.append("executed")
            return "done"

        task = create_background_task(sample_coro())
        await task

        assert result_holder == ["executed"]

    @pytest.mark.asyncio
    async def test_logs_error_on_exception(self):
        """Should log error when task raises exception"""

        async def failing_coro():
            raise ValueError("Test error")

        with patch("src.utils.async_utils.logger") as mock_logger:
            task = create_background_task(
                failing_coro(),
                context="Test context",
            )

            # Wait for task to complete (and fail)
            await asyncio.sleep(0.1)

            # Verify error was logged
            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert "Test context" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_calls_on_error_callback(self):
        """Should call on_error callback when task fails"""
        error_callback = Mock()

        async def failing_coro():
            raise ValueError("Test error")

        task = create_background_task(
            failing_coro(),
            context="Test",
            on_error=error_callback,
        )

        # Wait for task to complete
        await asyncio.sleep(0.1)

        # Verify callback was called with exception
        error_callback.assert_called_once()
        call_arg = error_callback.call_args[0][0]
        assert isinstance(call_arg, ValueError)

    @pytest.mark.asyncio
    async def test_handles_cancelled_task(self):
        """Should handle cancelled tasks gracefully"""

        async def slow_coro():
            await asyncio.sleep(10)

        task = create_background_task(slow_coro(), context="Slow task")

        # Cancel the task
        task.cancel()

        # Should not raise
        try:
            await task
        except asyncio.CancelledError:
            pass  # Expected

    @pytest.mark.asyncio
    async def test_context_parameter_optional(self):
        """Context parameter should be optional"""

        async def sample_coro():
            return "done"

        # Should not raise
        task = create_background_task(sample_coro())
        result = await task
        assert result == "done"

    @pytest.mark.asyncio
    async def test_on_error_parameter_optional(self):
        """on_error parameter should be optional"""

        async def failing_coro():
            raise ValueError("Test")

        # Should not raise even without on_error callback
        task = create_background_task(failing_coro(), context="Test")

        # Wait for task to complete
        await asyncio.sleep(0.1)

    @pytest.mark.asyncio
    async def test_preserves_return_value(self):
        """Should preserve coroutine return value"""

        async def sample_coro():
            return {"key": "value", "count": 42}

        task = create_background_task(sample_coro())
        result = await task

        assert result == {"key": "value", "count": 42}
