"""
Integration tests for src/integrations/slack/adapter.py
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from slack_sdk.errors import SlackApiError

from src.domain.enums import Category, ContentStatus, Difficulty, ReportType
from src.domain.models import BotStatus, ContentRecord, ReportData, SlackMessage
from src.integrations.slack.adapter import SlackAdapter


@pytest.fixture
def slack_adapter(mock_settings):
    """Create SlackAdapter with mocked client"""
    from config.settings import get_settings

    get_settings.cache_clear()

    with patch("src.integrations.slack.adapter.AsyncWebClient") as MockClient:
        client = AsyncMock()
        client.chat_postMessage = AsyncMock(return_value={"ok": True, "ts": "123.456"})
        client.auth_test = AsyncMock(return_value={"ok": True})
        client.conversations_open = AsyncMock(return_value={"channel": {"id": "D123"}})
        MockClient.return_value = client

        adapter = SlackAdapter()
        adapter.client = client
        yield adapter


class TestSendMessage:
    @pytest.mark.asyncio
    async def test_success_returns_timestamp(self, slack_adapter):
        msg = SlackMessage(channel="C123", text="hello")
        ts = await slack_adapter.send_message(msg)
        assert ts == "123.456"
        slack_adapter.client.chat_postMessage.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_api_error_returns_none(self, slack_adapter):
        slack_adapter.client.chat_postMessage.side_effect = SlackApiError(
            message="error", response={"ok": False}
        )
        msg = SlackMessage(channel="C123", text="hello")
        ts = await slack_adapter.send_message(msg)
        assert ts is None

    @pytest.mark.asyncio
    async def test_includes_blocks(self, slack_adapter):
        blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": "test"}}]
        msg = SlackMessage(channel="C123", text="hello", blocks=blocks)
        await slack_adapter.send_message(msg)
        call_kwargs = slack_adapter.client.chat_postMessage.call_args
        assert call_kwargs.kwargs.get("blocks") == blocks or call_kwargs[1].get("blocks") == blocks


class TestSendContentNotification:
    @pytest.fixture
    def sample_content(self):
        return ContentRecord(
            id=1,
            title="Test Title",
            category=Category.NETWORK,
            difficulty=Difficulty.INTERMEDIATE,
            summary="Test summary content",
            content="Test summary content",
            tags=["tag1", "tag2"],
            author="TestUser",
            status=ContentStatus.DRAFT,
        )

    @pytest.mark.asyncio
    async def test_sends_message(self, slack_adapter, sample_content):
        ts = await slack_adapter.send_content_notification(sample_content)
        assert ts == "123.456"

    @pytest.mark.asyncio
    async def test_includes_notion_link(self, slack_adapter, sample_content):
        sample_content.notion_url = "https://notion.so/page"
        await slack_adapter.send_content_notification(sample_content)
        call_args = slack_adapter.client.chat_postMessage.call_args
        blocks = call_args.kwargs.get("blocks", call_args[1].get("blocks", []))
        # Find notion link block
        has_notion_link = any("notion.so/page" in str(block) for block in blocks)
        assert has_notion_link

    @pytest.mark.asyncio
    async def test_without_notion_link(self, slack_adapter, sample_content):
        sample_content.notion_url = None
        await slack_adapter.send_content_notification(sample_content)
        call_args = slack_adapter.client.chat_postMessage.call_args
        blocks = call_args.kwargs.get("blocks", call_args[1].get("blocks", []))
        has_notion_link = any("자세히 보기" in str(block) for block in blocks)
        assert not has_notion_link

    @pytest.mark.asyncio
    async def test_includes_tags(self, slack_adapter, sample_content):
        await slack_adapter.send_content_notification(sample_content)
        call_args = slack_adapter.client.chat_postMessage.call_args
        blocks = call_args.kwargs.get("blocks", call_args[1].get("blocks", []))
        has_tags = any("tag1" in str(block) for block in blocks)
        assert has_tags


class TestSendErrorNotification:
    @pytest.mark.asyncio
    async def test_sends_to_channel(self, slack_adapter):
        await slack_adapter.send_error_notification("Test error")
        slack_adapter.client.chat_postMessage.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_sends_dm_when_user_id(self, slack_adapter):
        await slack_adapter.send_error_notification("error", user_id="U123")
        slack_adapter.client.conversations_open.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_includes_error_context(self, slack_adapter):
        ctx = {"key": "value"}
        await slack_adapter.send_error_notification("error", context=ctx)
        call_args = slack_adapter.client.chat_postMessage.call_args
        blocks = call_args.kwargs.get("blocks", call_args[1].get("blocks", []))
        has_context = any("value" in str(block) for block in blocks)
        assert has_context


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_returns_true_on_success(self, slack_adapter):
        result = await slack_adapter.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_on_failure(self, slack_adapter):
        slack_adapter.client.auth_test.side_effect = SlackApiError(
            message="error", response={"ok": False}
        )
        result = await slack_adapter.health_check()
        assert result is False


class TestSendStatus:
    @pytest.mark.asyncio
    async def test_running_status(self, slack_adapter):
        status = BotStatus(
            is_running=True,
            is_paused=False,
            total_generated=10,
            active_schedules=["07:00", "19:00"],
            next_execution=datetime(2026, 2, 6, 7, 0),
            last_execution=datetime(2026, 2, 5, 7, 0),
            uptime_seconds=3600,
        )
        ts = await slack_adapter.send_status(status, channel="C123")
        assert ts == "123.456"
        call_args = slack_adapter.client.chat_postMessage.call_args
        blocks = call_args.kwargs.get("blocks", call_args[1].get("blocks", []))
        blocks_str = str(blocks)
        assert "실행 중" in blocks_str
        assert "07:00, 19:00" in blocks_str
        assert "10개" in blocks_str

    @pytest.mark.asyncio
    async def test_paused_status(self, slack_adapter):
        status = BotStatus(is_running=True, is_paused=True, total_generated=0)
        await slack_adapter.send_status(status, channel="C123")
        call_args = slack_adapter.client.chat_postMessage.call_args
        blocks = call_args.kwargs.get("blocks", call_args[1].get("blocks", []))
        blocks_str = str(blocks)
        assert "일시정지" in blocks_str

    @pytest.mark.asyncio
    async def test_stopped_status(self, slack_adapter):
        status = BotStatus(is_running=False, is_paused=False, total_generated=0)
        await slack_adapter.send_status(status, channel="C123")
        call_args = slack_adapter.client.chat_postMessage.call_args
        blocks = call_args.kwargs.get("blocks", call_args[1].get("blocks", []))
        blocks_str = str(blocks)
        assert "중지됨" in blocks_str

    @pytest.mark.asyncio
    async def test_minimal_status_omits_optional_blocks(self, slack_adapter):
        """Optional fields that are empty should not render their blocks"""
        status = BotStatus(is_running=True, is_paused=False, total_generated=0)
        await slack_adapter.send_status(status, channel="C123")
        call_args = slack_adapter.client.chat_postMessage.call_args
        blocks = call_args.kwargs.get("blocks", call_args[1].get("blocks", []))
        blocks_str = str(blocks)
        assert "활성 스케줄" not in blocks_str
        assert "다음 실행" not in blocks_str
        assert "마지막 실행" not in blocks_str
        assert "가동 시간" not in blocks_str


class TestSendReportNotification:
    @pytest.fixture
    def sample_report(self):
        return ReportData(
            report_type=ReportType.WEEKLY,
            period_start=datetime(2026, 1, 27),
            period_end=datetime(2026, 2, 2),
            total_count=7,
            success_count=6,
            failed_count=1,
            retry_count=2,
            category_distribution={"network": 3, "os": 2, "algorithm": 1},
            generated_at=datetime(2026, 2, 3),
        )

    @pytest.mark.asyncio
    async def test_weekly_report(self, slack_adapter, sample_report):
        ts = await slack_adapter.send_report_notification(sample_report)
        assert ts == "123.456"
        call_args = slack_adapter.client.chat_postMessage.call_args
        blocks = call_args.kwargs.get("blocks", call_args[1].get("blocks", []))
        blocks_str = str(blocks)
        assert "주간" in blocks_str
        assert "7건" in blocks_str
        assert "6건" in blocks_str
        assert "1건" in blocks_str
        assert "2건" in blocks_str

    @pytest.mark.asyncio
    async def test_monthly_report_with_notion_url(self, slack_adapter):
        report = ReportData(
            report_type=ReportType.MONTHLY,
            period_start=datetime(2026, 1, 1),
            period_end=datetime(2026, 1, 31),
            total_count=30,
            success_count=28,
            failed_count=2,
            retry_count=3,
            category_distribution={"network": 10},
            generated_at=datetime(2026, 2, 1),
        )
        await slack_adapter.send_report_notification(report, notion_url="https://notion.so/report")
        call_args = slack_adapter.client.chat_postMessage.call_args
        blocks = call_args.kwargs.get("blocks", call_args[1].get("blocks", []))
        blocks_str = str(blocks)
        assert "월간" in blocks_str
        assert "notion.so/report" in blocks_str

    @pytest.mark.asyncio
    async def test_with_uncovered_categories(self, slack_adapter, sample_report):
        sample_report.uncovered_categories = ["security", "devops"]
        await slack_adapter.send_report_notification(sample_report)
        call_args = slack_adapter.client.chat_postMessage.call_args
        blocks = call_args.kwargs.get("blocks", call_args[1].get("blocks", []))
        blocks_str = str(blocks)
        assert "미다룬 카테고리" in blocks_str


class TestSendHelp:
    @pytest.mark.asyncio
    async def test_sends_help_message(self, slack_adapter):
        ts = await slack_adapter.send_help(channel="C123")
        assert ts == "123.456"
        slack_adapter.client.chat_postMessage.assert_awaited_once()
        call_args = slack_adapter.client.chat_postMessage.call_args
        blocks = call_args.kwargs.get("blocks", call_args[1].get("blocks", []))
        blocks_str = str(blocks)
        assert "/daily-bot" in blocks_str
        assert "time" in blocks_str
        assert "pause" in blocks_str
        assert "now" in blocks_str
        assert "request" in blocks_str

    @pytest.mark.asyncio
    async def test_returns_timestamp(self, slack_adapter):
        ts = await slack_adapter.send_help(channel="C123")
        assert isinstance(ts, str)
        assert ts == "123.456"
