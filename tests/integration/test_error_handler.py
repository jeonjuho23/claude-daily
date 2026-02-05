"""
Integration tests for src/errors/handler.py
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.enums import ExecutionStatus
from src.domain.models import ExecutionLog
from src.errors.handler import (
    ErrorHandler,
    NonRetryableError,
    RetryableError,
    is_retryable_error,
)


class TestExecuteWithRetry:
    """Tests for execute_with_retry method"""

    @pytest.fixture
    def handler(self):
        return ErrorHandler(max_retries=3, base_interval=1)

    @pytest.fixture
    def execution_log(self):
        return ExecutionLog(id=1, status=ExecutionStatus.PENDING)

    @pytest.fixture
    def update_callback(self):
        return AsyncMock()

    @pytest.mark.asyncio
    @patch("src.errors.handler.asyncio.sleep", new_callable=AsyncMock)
    async def test_success_on_first_attempt(self, mock_sleep, handler):
        func = AsyncMock(return_value="result")
        result = await handler.execute_with_retry(func)
        assert result == "result"
        func.assert_awaited_once()
        mock_sleep.assert_not_awaited()

    @pytest.mark.asyncio
    @patch("src.errors.handler.asyncio.sleep", new_callable=AsyncMock)
    async def test_success_after_retry(self, mock_sleep, handler):
        func = AsyncMock(side_effect=[Exception("fail"), "result"])
        result = await handler.execute_with_retry(func)
        assert result == "result"
        assert func.await_count == 2
        mock_sleep.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("src.errors.handler.asyncio.sleep", new_callable=AsyncMock)
    async def test_all_retries_exhausted(self, mock_sleep, handler):
        func = AsyncMock(side_effect=Exception("always fails"))
        with pytest.raises(Exception, match="always fails"):
            await handler.execute_with_retry(func)
        assert func.await_count == 3  # max_retries = 3

    @pytest.mark.asyncio
    @patch("src.errors.handler.asyncio.sleep", new_callable=AsyncMock)
    async def test_non_retryable_error_stops(self, mock_sleep, handler):
        func = AsyncMock(side_effect=NonRetryableError("fatal"))
        with pytest.raises(NonRetryableError):
            await handler.execute_with_retry(func)
        func.assert_awaited_once()
        mock_sleep.assert_not_awaited()

    @pytest.mark.asyncio
    @patch("src.errors.handler.asyncio.sleep", new_callable=AsyncMock)
    async def test_updates_execution_log_on_success(
        self, mock_sleep, handler, execution_log, update_callback
    ):
        func = AsyncMock(return_value="ok")
        await handler.execute_with_retry(
            func, execution_log=execution_log, update_log_callback=update_callback
        )
        # Log should be updated to SUCCESS
        assert execution_log.status == ExecutionStatus.SUCCESS
        assert update_callback.await_count >= 1

    @pytest.mark.asyncio
    @patch("src.errors.handler.asyncio.sleep", new_callable=AsyncMock)
    async def test_updates_execution_log_on_failure(
        self, mock_sleep, handler, execution_log, update_callback
    ):
        func = AsyncMock(side_effect=Exception("fail"))
        with pytest.raises(Exception, match="fail"):
            await handler.execute_with_retry(
                func, execution_log=execution_log, update_log_callback=update_callback
            )
        assert execution_log.status == ExecutionStatus.FAILED

    @pytest.mark.asyncio
    @patch("src.errors.handler.asyncio.sleep", new_callable=AsyncMock)
    async def test_calls_error_callback_on_final_fail(self, mock_sleep):
        error_cb = AsyncMock()
        handler = ErrorHandler(max_retries=2, base_interval=1, on_error_callback=error_cb)
        func = AsyncMock(side_effect=Exception("error"))
        with pytest.raises(Exception, match="error"):
            await handler.execute_with_retry(func)
        error_cb.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("src.errors.handler.asyncio.sleep", new_callable=AsyncMock)
    async def test_increments_attempt_count(
        self, mock_sleep, handler, execution_log, update_callback
    ):
        func = AsyncMock(side_effect=[Exception("fail"), "ok"])
        await handler.execute_with_retry(
            func, execution_log=execution_log, update_log_callback=update_callback
        )
        assert execution_log.attempt_count == 2

    @pytest.mark.asyncio
    @patch("src.errors.handler.asyncio.sleep", new_callable=AsyncMock)
    async def test_sets_error_message_on_failure(
        self, mock_sleep, handler, execution_log, update_callback
    ):
        func = AsyncMock(side_effect=Exception("specific error"))
        with pytest.raises(Exception, match="specific error"):
            await handler.execute_with_retry(
                func, execution_log=execution_log, update_log_callback=update_callback
            )
        assert execution_log.error_message == "specific error"

    @pytest.mark.asyncio
    @patch("src.errors.handler.asyncio.sleep", new_callable=AsyncMock)
    async def test_sets_completed_at_on_success(
        self, mock_sleep, handler, execution_log, update_callback
    ):
        func = AsyncMock(return_value="ok")
        await handler.execute_with_retry(
            func, execution_log=execution_log, update_log_callback=update_callback
        )
        assert execution_log.completed_at is not None
        assert isinstance(execution_log.completed_at, datetime)

    @pytest.mark.asyncio
    @patch("src.errors.handler.asyncio.sleep", new_callable=AsyncMock)
    async def test_sets_completed_at_on_failure(
        self, mock_sleep, handler, execution_log, update_callback
    ):
        func = AsyncMock(side_effect=Exception("fail"))
        with pytest.raises(Exception, match="fail"):
            await handler.execute_with_retry(
                func, execution_log=execution_log, update_log_callback=update_callback
            )
        assert execution_log.completed_at is not None
        assert isinstance(execution_log.completed_at, datetime)

    @pytest.mark.asyncio
    @patch("src.errors.handler.asyncio.sleep", new_callable=AsyncMock)
    async def test_wait_time_increases_with_attempts(self, mock_sleep, handler):
        func = AsyncMock(side_effect=[Exception("fail1"), Exception("fail2"), "ok"])
        await handler.execute_with_retry(func)
        # base_interval=1, so wait times should be 1*1*60=60, then 1*2*60=120
        assert mock_sleep.await_count == 2
        # Check first wait is 60 seconds (1 minute * attempt 1)
        assert mock_sleep.await_args_list[0][0][0] == 60
        # Check second wait is 120 seconds (1 minute * attempt 2)
        assert mock_sleep.await_args_list[1][0][0] == 120

    @pytest.mark.asyncio
    @patch("src.errors.handler.asyncio.sleep", new_callable=AsyncMock)
    async def test_status_transitions_correctly(
        self, mock_sleep, handler, execution_log, update_callback
    ):
        func = AsyncMock(side_effect=[Exception("fail"), "ok"])
        await handler.execute_with_retry(
            func, execution_log=execution_log, update_log_callback=update_callback
        )
        # Should have transitions: RUNNING -> RETRY -> SUCCESS
        # Check final status
        assert execution_log.status == ExecutionStatus.SUCCESS


class TestCalculateNextRetryTime:
    def test_returns_datetime(self):
        handler = ErrorHandler(max_retries=5, base_interval=5)
        result = handler.calculate_next_retry_time(1)
        assert isinstance(result, datetime)

    def test_different_attempts_return_different_times(self):
        handler = ErrorHandler(max_retries=5, base_interval=5)
        time1 = handler.calculate_next_retry_time(1)
        time2 = handler.calculate_next_retry_time(2)
        # time2 should be later than time1
        assert time2 > time1


class TestShouldRetry:
    @pytest.fixture
    def handler(self):
        return ErrorHandler(max_retries=5, base_interval=5)

    def test_under_max_returns_true(self, handler):
        assert handler.should_retry(1, RetryableError("err")) is True

    def test_at_max_returns_false(self, handler):
        assert handler.should_retry(5, RetryableError("err")) is False

    def test_over_max_returns_false(self, handler):
        assert handler.should_retry(6, RetryableError("err")) is False

    def test_non_retryable_returns_false(self, handler):
        assert handler.should_retry(1, NonRetryableError("err")) is False

    def test_timeout_error_returns_true(self, handler):
        assert handler.should_retry(1, Exception("timeout occurred")) is True

    def test_connection_error_returns_true(self, handler):
        assert handler.should_retry(1, Exception("connection refused")) is True

    def test_rate_limit_error_returns_true(self, handler):
        assert handler.should_retry(1, Exception("rate limit exceeded")) is True

    def test_503_error_returns_true(self, handler):
        assert handler.should_retry(1, Exception("HTTP 503 Service Unavailable")) is True

    def test_502_error_returns_true(self, handler):
        assert handler.should_retry(1, Exception("HTTP 502 Bad Gateway")) is True

    def test_500_error_returns_true(self, handler):
        assert handler.should_retry(1, Exception("HTTP 500 Internal Server Error")) is True

    def test_temporarily_error_returns_true(self, handler):
        assert handler.should_retry(1, Exception("temporarily unavailable")) is True

    def test_unknown_error_returns_false(self, handler):
        assert handler.should_retry(1, Exception("some random error")) is False

    def test_retryable_error_instance_returns_true(self, handler):
        assert handler.should_retry(1, RetryableError("retry this")) is True


class TestIsRetryableError:
    def test_retryable_error_returns_true(self):
        assert is_retryable_error(RetryableError("err")) is True

    def test_non_retryable_returns_false(self):
        assert is_retryable_error(NonRetryableError("err")) is False

    def test_timeout_returns_true(self):
        assert is_retryable_error(Exception("timeout")) is True

    def test_connection_refused_returns_true(self):
        assert is_retryable_error(Exception("connection refused")) is True

    def test_connection_reset_returns_true(self):
        assert is_retryable_error(Exception("connection reset")) is True

    def test_rate_limit_returns_true(self):
        assert is_retryable_error(Exception("rate limit")) is True

    def test_too_many_requests_returns_true(self):
        assert is_retryable_error(Exception("too many requests")) is True

    def test_service_unavailable_returns_true(self):
        assert is_retryable_error(Exception("service unavailable")) is True

    def test_bad_gateway_returns_true(self):
        assert is_retryable_error(Exception("bad gateway")) is True

    def test_internal_server_error_returns_true(self):
        assert is_retryable_error(Exception("internal server error")) is True

    def test_temporarily_unavailable_returns_true(self):
        assert is_retryable_error(Exception("temporarily unavailable")) is True

    def test_unknown_returns_false(self):
        assert is_retryable_error(Exception("random")) is False

    def test_case_insensitive(self):
        assert is_retryable_error(Exception("TIMEOUT")) is True
        assert is_retryable_error(Exception("Connection Refused")) is True


class TestExtractRetryAfter:
    def test_returns_none_for_normal_error(self):
        handler = ErrorHandler(max_retries=3, base_interval=1)
        result = handler._extract_retry_after(Exception("normal error"))
        assert result is None

    def test_returns_30_for_429_error(self):
        handler = ErrorHandler(max_retries=3, base_interval=1)
        result = handler._extract_retry_after(Exception("HTTP 429 Too Many Requests"))
        assert result == 30

    def test_returns_30_for_rate_limit_error(self):
        handler = ErrorHandler(max_retries=3, base_interval=1)
        result = handler._extract_retry_after(Exception("rate_limited"))
        assert result == 30

    def test_extracts_retry_after_header(self):
        handler = ErrorHandler(max_retries=3, base_interval=1)
        error = Exception("api error")
        error.response = MagicMock()
        error.response.headers = {"Retry-After": "60"}
        result = handler._extract_retry_after(error)
        assert result == 60

    def test_extracts_retry_after_header_as_int(self):
        handler = ErrorHandler(max_retries=3, base_interval=1)
        error = Exception("api error")
        error.response = MagicMock()
        error.response.headers = {"Retry-After": "120"}
        result = handler._extract_retry_after(error)
        assert result == 120

    def test_returns_none_when_no_response_attribute(self):
        handler = ErrorHandler(max_retries=3, base_interval=1)
        error = Exception("no response attribute")
        result = handler._extract_retry_after(error)
        assert result is None

    def test_returns_none_when_no_headers_attribute(self):
        handler = ErrorHandler(max_retries=3, base_interval=1)
        error = Exception("no headers")
        error.response = MagicMock(spec=[])
        result = handler._extract_retry_after(error)
        assert result is None

    def test_429_in_lowercase(self):
        handler = ErrorHandler(max_retries=3, base_interval=1)
        result = handler._extract_retry_after(Exception("error 429"))
        assert result == 30

    def test_rate_limit_case_insensitive(self):
        handler = ErrorHandler(max_retries=3, base_interval=1)
        result = handler._extract_retry_after(Exception("Rate_Limit exceeded"))
        assert result == 30


class TestCreateRetryDecorator:
    def test_creates_decorator_with_default_settings(self):
        handler = ErrorHandler(max_retries=5, base_interval=5)
        decorator = handler.create_retry_decorator()
        assert decorator is not None

    def test_creates_decorator_with_custom_attempts(self):
        handler = ErrorHandler(max_retries=5, base_interval=5)
        decorator = handler.create_retry_decorator(max_attempts=3)
        assert decorator is not None
