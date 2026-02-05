"""
Integration tests for src/integrations/slack/command_handler.py
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.domain.enums import SlackCommandType


@pytest.fixture
def command_handler(mock_settings):
    """Create CommandHandler with mocked dependencies"""
    from config.settings import get_settings

    get_settings.cache_clear()

    with patch("src.integrations.slack.command_handler.AsyncApp"):
        from src.integrations.slack.command_handler import CommandHandler

        handler = CommandHandler()
        yield handler


class TestProcessCommand:
    @pytest.mark.asyncio
    async def test_empty_text_returns_help(self, command_handler):
        result = await command_handler._process_command("", "U123", "C123")
        assert "도움말" in result or "help" in result.lower()

    @pytest.mark.asyncio
    async def test_unknown_command_returns_error(self, command_handler):
        result = await command_handler._process_command("foobar", "U123", "C123")
        assert "알 수 없는" in result

    @pytest.mark.asyncio
    async def test_help_command(self, command_handler):
        result = await command_handler._process_command("help", "U123", "C123")
        assert "도움말" in result


class TestTimeCommand:
    @pytest.mark.asyncio
    async def test_valid_time_calls_callback(self, command_handler):
        cb = AsyncMock(return_value="OK")
        command_handler.set_callback(SlackCommandType.TIME, cb)
        result = await command_handler._process_command("time 08:00", "U123", "C123")
        cb.assert_awaited_once_with("08:00", "U123", "C123")
        assert result == "OK"

    @pytest.mark.asyncio
    async def test_missing_args_returns_error(self, command_handler):
        result = await command_handler._process_command("time", "U123", "C123")
        assert "시간을 입력" in result

    @pytest.mark.asyncio
    async def test_invalid_format_returns_error(self, command_handler):
        result = await command_handler._process_command("time abc", "U123", "C123")
        assert "잘못된" in result


class TestAddRemoveCommands:
    @pytest.mark.asyncio
    async def test_add_valid_time(self, command_handler):
        cb = AsyncMock(return_value="Added")
        command_handler.set_callback(SlackCommandType.ADD, cb)
        result = await command_handler._process_command("add 09:30", "U123", "C123")
        cb.assert_awaited_once_with("09:30", "U123", "C123")

    @pytest.mark.asyncio
    async def test_add_missing_args(self, command_handler):
        result = await command_handler._process_command("add", "U123", "C123")
        assert "추가할 시간" in result

    @pytest.mark.asyncio
    async def test_remove_valid_time(self, command_handler):
        cb = AsyncMock(return_value="Removed")
        command_handler.set_callback(SlackCommandType.REMOVE, cb)
        result = await command_handler._process_command("remove 09:30", "U123", "C123")
        cb.assert_awaited_once_with("09:30", "U123", "C123")

    @pytest.mark.asyncio
    async def test_remove_missing_args(self, command_handler):
        result = await command_handler._process_command("remove", "U123", "C123")
        assert "삭제할 시간" in result


class TestControlCommands:
    @pytest.mark.asyncio
    async def test_list_calls_callback(self, command_handler):
        cb = AsyncMock(return_value="Schedules")
        command_handler.set_callback(SlackCommandType.LIST, cb)
        result = await command_handler._process_command("list", "U123", "C123")
        cb.assert_awaited_once_with("U123", "C123")

    @pytest.mark.asyncio
    async def test_pause_calls_callback(self, command_handler):
        cb = AsyncMock(return_value="Paused")
        command_handler.set_callback(SlackCommandType.PAUSE, cb)
        result = await command_handler._process_command("pause", "U123", "C123")
        cb.assert_awaited_once_with("U123", "C123")

    @pytest.mark.asyncio
    async def test_resume_calls_callback(self, command_handler):
        cb = AsyncMock(return_value="Resumed")
        command_handler.set_callback(SlackCommandType.RESUME, cb)
        result = await command_handler._process_command("resume", "U123", "C123")
        cb.assert_awaited_once_with("U123", "C123")

    @pytest.mark.asyncio
    async def test_now_calls_callback(self, command_handler):
        cb = AsyncMock(return_value="Starting")
        command_handler.set_callback(SlackCommandType.NOW, cb)
        result = await command_handler._process_command("now", "U123", "C123")
        cb.assert_awaited_once_with("U123", "C123")

    @pytest.mark.asyncio
    async def test_status_calls_callback(self, command_handler):
        cb = AsyncMock(return_value="Status")
        command_handler.set_callback(SlackCommandType.STATUS, cb)
        result = await command_handler._process_command("status", "U123", "C123")
        cb.assert_awaited_once_with("U123", "C123")


class TestRequestCommand:
    @pytest.mark.asyncio
    async def test_quoted_topic(self, command_handler):
        cb = AsyncMock(return_value="Requested")
        command_handler.set_callback(SlackCommandType.REQUEST, cb)
        result = await command_handler._process_command('request "HTTP 프로토콜"', "U123", "C123")
        cb.assert_awaited_once_with("HTTP 프로토콜", "U123", "C123")

    @pytest.mark.asyncio
    async def test_unquoted_topic(self, command_handler):
        cb = AsyncMock(return_value="Requested")
        command_handler.set_callback(SlackCommandType.REQUEST, cb)
        result = await command_handler._process_command("request HTTP", "U123", "C123")
        cb.assert_awaited_once_with("HTTP", "U123", "C123")

    @pytest.mark.asyncio
    async def test_missing_topic_returns_error(self, command_handler):
        result = await command_handler._process_command("request", "U123", "C123")
        assert "요청할 주제" in result


class TestRemoveTimeValidation:
    @pytest.mark.asyncio
    async def test_remove_invalid_time_format(self, command_handler):
        result = await command_handler._process_command("remove invalid", "U123", "C123")
        assert "잘못된 시간 형식" in result

    @pytest.mark.asyncio
    async def test_remove_valid_time_calls_callback(self, command_handler):
        cb = AsyncMock(return_value="Removed")
        command_handler.set_callback(SlackCommandType.REMOVE, cb)
        result = await command_handler._process_command("remove 19:00", "U123", "C123")
        cb.assert_awaited_once_with("19:00", "U123", "C123")
        assert result == "Removed"


class TestNoCallbackRegistered:
    @pytest.mark.asyncio
    async def test_returns_error_when_no_callback(self, command_handler):
        result = await command_handler._process_command("time 08:00", "U123", "C123")
        assert "핸들러가 설정되지" in result
