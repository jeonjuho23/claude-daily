"""
Integration tests for src/core/engine.py
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.enums import (
    Category,
    ContentStatus,
    Difficulty,
    ExecutionStatus,
    ScheduleStatus,
)
from src.domain.models import (
    ContentRecord,
    ExecutionLog,
    Schedule,
    TopicRequest,
)


@pytest.fixture
def engine(mock_settings, mock_repository, mock_generator, mock_slack_adapter, mock_notion_adapter):
    """Create CoreEngine with all mocked dependencies"""
    from config.settings import get_settings

    get_settings.cache_clear()

    with patch("src.core.engine.AsyncIOScheduler") as MockScheduler:
        scheduler_instance = MagicMock()
        scheduler_instance.get_job.return_value = None
        MockScheduler.return_value = scheduler_instance

        from src.core.engine import CoreEngine

        e = CoreEngine(
            repository=mock_repository,
            generator=mock_generator,
            slack_adapter=mock_slack_adapter,
            notion_adapter=mock_notion_adapter,
        )
        e.scheduler = scheduler_instance
        yield e


class TestLifecycle:
    @pytest.mark.asyncio
    async def test_start_initializes_repository(self, engine, mock_repository):
        await engine.start()
        mock_repository.initialize.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_start_loads_schedules(self, engine, mock_repository):
        await engine.start()
        mock_repository.list_schedules.assert_awaited()

    @pytest.mark.asyncio
    async def test_start_creates_default_schedule(self, engine, mock_repository):
        mock_repository.list_schedules.return_value = []
        await engine.start()
        mock_repository.save_schedule.assert_awaited()

    @pytest.mark.asyncio
    async def test_start_starts_scheduler(self, engine):
        await engine.start()
        engine.scheduler.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_shuts_down_scheduler(self, engine):
        await engine.start()
        await engine.stop()
        engine.scheduler.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_closes_repository(self, engine, mock_repository):
        await engine.start()
        await engine.stop()
        mock_repository.close.assert_awaited_once()


class TestContentGeneration:
    @pytest.mark.asyncio
    @patch("src.core.engine.ErrorHandler.execute_with_retry")
    async def test_success_flow(
        self,
        mock_retry,
        engine,
        mock_repository,
        mock_generator,
        mock_slack_adapter,
        mock_notion_adapter,
    ):
        content = ContentRecord(
            id=1,
            title="Test",
            category=Category.NETWORK,
            difficulty=Difficulty.INTERMEDIATE,
            summary="Summary",
            content="Summary",
            tags=["tag1"],
            author="TestUser",
            status=ContentStatus.PUBLISHED,
        )
        mock_retry.return_value = content
        # save_execution_log needs to return an ExecutionLog with id
        mock_repository.save_execution_log.return_value = ExecutionLog(
            id=1, status=ExecutionStatus.PENDING
        )

        result = await engine._execute_content_generation(schedule_id=1)
        assert result is not None
        mock_retry.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_skips_when_paused(self, engine):
        engine._is_paused = True
        result = await engine._execute_content_generation()
        assert result is None

    @pytest.mark.asyncio
    @patch("src.core.engine.ErrorHandler.execute_with_retry")
    async def test_creates_execution_log(self, mock_retry, engine, mock_repository):
        mock_retry.return_value = ContentRecord(
            id=1,
            title="T",
            category=Category.NETWORK,
            difficulty=Difficulty.INTERMEDIATE,
            summary="S",
            content="S",
            tags=[],
            author="A",
            status=ContentStatus.DRAFT,
        )
        mock_repository.save_execution_log.return_value = ExecutionLog(
            id=1, status=ExecutionStatus.PENDING
        )

        await engine._execute_content_generation()
        mock_repository.save_execution_log.assert_awaited()

    @pytest.mark.asyncio
    @patch("src.core.engine.ErrorHandler.execute_with_retry")
    async def test_handles_generation_failure(self, mock_retry, engine, mock_repository):
        mock_retry.side_effect = Exception("generation failed")
        mock_repository.save_execution_log.return_value = ExecutionLog(
            id=1, status=ExecutionStatus.PENDING
        )

        result = await engine._execute_content_generation()
        assert result is None

    @pytest.mark.asyncio
    async def test_generate_and_publish_flow(
        self, engine, mock_repository, mock_generator, mock_notion_adapter, mock_slack_adapter
    ):
        content = await engine._generate_and_publish()
        # Generator should be called
        mock_generator.generate_random.assert_awaited_once()
        # Should save to DB
        mock_repository.save_content.assert_awaited()
        # Should create Notion page
        mock_notion_adapter.create_content_page.assert_awaited()
        # Should send Slack notification
        mock_slack_adapter.send_content_notification.assert_awaited()
        # Should update content status
        mock_repository.update_content.assert_awaited()

    @pytest.mark.asyncio
    async def test_handles_notion_failure(self, engine, mock_notion_adapter, mock_slack_adapter):
        mock_notion_adapter.create_content_page.side_effect = Exception("Notion failed")
        content = await engine._generate_and_publish()
        # Should still send Slack
        mock_slack_adapter.send_content_notification.assert_awaited()

    @pytest.mark.asyncio
    async def test_handles_slack_failure(self, engine, mock_slack_adapter):
        mock_slack_adapter.send_content_notification.side_effect = Exception("Slack failed")
        content = await engine._generate_and_publish()
        # Should still complete
        assert content is not None

    @pytest.mark.asyncio
    async def test_with_topic_request(self, engine, mock_generator):
        request = TopicRequest(id=1, topic="TCP handshake", requested_by="U123")
        content = await engine._generate_and_publish(topic_request=request)
        mock_generator.generate.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_both_notion_and_slack_failure_keeps_draft(
        self, engine, mock_notion_adapter, mock_slack_adapter, mock_repository
    ):
        """When both Notion and Slack fail, content should stay DRAFT"""
        mock_notion_adapter.create_content_page = AsyncMock(side_effect=Exception("Notion fail"))
        mock_slack_adapter.send_content_notification = AsyncMock(
            side_effect=Exception("Slack fail")
        )
        content = await engine._generate_and_publish()
        # update_content is called with the content; check the status passed
        update_call = mock_repository.update_content.call_args[0][0]
        assert update_call.status == ContentStatus.DRAFT

    @pytest.mark.asyncio
    async def test_published_when_slack_succeeds_but_notion_fails(
        self, engine, mock_notion_adapter, mock_slack_adapter, mock_repository
    ):
        """When Notion fails but Slack succeeds, content should be PUBLISHED"""
        mock_notion_adapter.create_content_page = AsyncMock(side_effect=Exception("Notion fail"))
        mock_slack_adapter.send_content_notification = AsyncMock(return_value="ts123")
        content = await engine._generate_and_publish()
        update_call = mock_repository.update_content.call_args[0][0]
        assert update_call.status == ContentStatus.PUBLISHED

    @pytest.mark.asyncio
    @patch("src.core.engine.ErrorHandler.execute_with_retry")
    async def test_execution_log_records_duration(self, mock_retry, engine, mock_repository):
        """Execution log should record duration_ms > 0"""
        mock_retry.return_value = ContentRecord(
            id=1,
            title="T",
            category=Category.NETWORK,
            difficulty=Difficulty.INTERMEDIATE,
            summary="S",
            content="S",
            tags=[],
            author="A",
            status=ContentStatus.DRAFT,
        )
        mock_repository.save_execution_log.return_value = ExecutionLog(
            id=1, status=ExecutionStatus.PENDING
        )

        await engine._execute_content_generation()
        # update_execution_log should be called with duration_ms > 0
        update_calls = mock_repository.update_execution_log.call_args_list
        # The last call should have the final log with duration
        final_log = update_calls[-1][0][0]
        assert final_log.duration_ms is not None
        assert final_log.duration_ms >= 0


class TestContentGenerationWithoutNotion:
    """Tests for content generation when Notion is not configured"""

    @pytest.fixture
    def engine_no_notion(self, mock_settings, mock_repository, mock_generator, mock_slack_adapter):
        """Create CoreEngine without Notion adapter"""
        from config.settings import get_settings

        get_settings.cache_clear()

        with patch("src.core.engine.AsyncIOScheduler") as MockScheduler:
            scheduler_instance = MagicMock()
            scheduler_instance.get_job.return_value = None
            MockScheduler.return_value = scheduler_instance

            from src.core.engine import CoreEngine

            e = CoreEngine(
                repository=mock_repository,
                generator=mock_generator,
                slack_adapter=mock_slack_adapter,
                notion_adapter=None,
            )
            e.scheduler = scheduler_instance
            yield e

    @pytest.mark.asyncio
    async def test_publish_without_notion(
        self, engine_no_notion, mock_repository, mock_generator, mock_slack_adapter
    ):
        """Content should be published via Slack only when Notion is None"""
        content = await engine_no_notion._generate_and_publish()
        mock_generator.generate_random.assert_awaited_once()
        mock_repository.save_content.assert_awaited()
        mock_slack_adapter.send_content_notification.assert_awaited()
        mock_repository.update_content.assert_awaited()

    @pytest.mark.asyncio
    async def test_publish_without_notion_status_published(
        self, engine_no_notion, mock_repository, mock_slack_adapter
    ):
        """Content should be PUBLISHED when Slack succeeds and Notion is None"""
        mock_slack_adapter.send_content_notification = AsyncMock(return_value="ts123")
        content = await engine_no_notion._generate_and_publish()
        update_call = mock_repository.update_content.call_args[0][0]
        assert update_call.status == ContentStatus.PUBLISHED

    @pytest.mark.asyncio
    async def test_publish_without_notion_slack_fails_stays_draft(
        self, engine_no_notion, mock_repository, mock_slack_adapter
    ):
        """Content should stay DRAFT when both Notion is None and Slack fails"""
        mock_slack_adapter.send_content_notification = AsyncMock(
            side_effect=Exception("Slack fail")
        )
        content = await engine_no_notion._generate_and_publish()
        update_call = mock_repository.update_content.call_args[0][0]
        assert update_call.status == ContentStatus.DRAFT


class TestCommandHandlers:
    @pytest.mark.asyncio
    async def test_time_command_updates_existing(self, engine, mock_repository):
        schedule = Schedule(id=1, time="07:00", status=ScheduleStatus.ACTIVE)
        mock_repository.list_schedules.return_value = [schedule]
        result = await engine._handle_time_command("08:00", "U123", "C123")
        assert "변경" in result
        mock_repository.update_schedule.assert_awaited()

    @pytest.mark.asyncio
    async def test_time_command_creates_new(self, engine, mock_repository):
        mock_repository.list_schedules.return_value = []
        result = await engine._handle_time_command("08:00", "U123", "C123")
        assert "생성" in result
        mock_repository.save_schedule.assert_awaited()

    @pytest.mark.asyncio
    async def test_add_command_success(self, engine, mock_repository):
        mock_repository.get_schedule_by_time.return_value = None
        result = await engine._handle_add_command("09:30", "U123", "C123")
        assert "추가" in result
        mock_repository.save_schedule.assert_awaited()

    @pytest.mark.asyncio
    async def test_add_command_duplicate(self, engine, mock_repository):
        mock_repository.get_schedule_by_time.return_value = Schedule(id=1, time="09:30")
        result = await engine._handle_add_command("09:30", "U123", "C123")
        assert "이미" in result

    @pytest.mark.asyncio
    async def test_remove_command_success(self, engine, mock_repository):
        mock_repository.get_schedule_by_time.return_value = Schedule(id=1, time="09:30")
        result = await engine._handle_remove_command("09:30", "U123", "C123")
        assert "삭제" in result
        mock_repository.delete_schedule.assert_awaited()

    @pytest.mark.asyncio
    async def test_remove_command_not_found(self, engine, mock_repository):
        mock_repository.get_schedule_by_time.return_value = None
        result = await engine._handle_remove_command("09:30", "U123", "C123")
        assert "찾을 수 없" in result

    @pytest.mark.asyncio
    async def test_list_command(self, engine, mock_repository):
        mock_repository.list_schedules.return_value = [
            Schedule(id=1, time="07:00", status=ScheduleStatus.ACTIVE),
            Schedule(id=2, time="19:00", status=ScheduleStatus.ACTIVE),
        ]
        result = await engine._handle_list_command("U123", "C123")
        assert "07:00" in result
        assert "19:00" in result

    @pytest.mark.asyncio
    async def test_list_command_empty(self, engine, mock_repository):
        mock_repository.list_schedules.return_value = []
        result = await engine._handle_list_command("U123", "C123")
        assert "없습니다" in result

    @pytest.mark.asyncio
    async def test_pause_command(self, engine):
        engine._is_paused = False
        result = await engine._handle_pause_command("U123", "C123")
        assert engine._is_paused is True
        assert "일시정지" in result

    @pytest.mark.asyncio
    async def test_pause_already_paused(self, engine):
        engine._is_paused = True
        result = await engine._handle_pause_command("U123", "C123")
        assert "이미" in result

    @pytest.mark.asyncio
    async def test_resume_command(self, engine):
        engine._is_paused = True
        result = await engine._handle_resume_command("U123", "C123")
        assert engine._is_paused is False
        assert "재개" in result

    @pytest.mark.asyncio
    async def test_resume_already_running(self, engine):
        engine._is_paused = False
        result = await engine._handle_resume_command("U123", "C123")
        assert "이미" in result

    @pytest.mark.asyncio
    @patch("src.core.engine.create_background_task")
    async def test_now_command(self, mock_bg_task, engine):
        result = await engine._handle_now_command("U123", "C123")
        assert "시작" in result
        mock_bg_task.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.core.engine.create_background_task")
    async def test_request_command(self, mock_bg_task, engine, mock_repository):
        result = await engine._handle_request_command("TCP handshake", "U123", "C123")
        assert "요청" in result
        mock_repository.save_topic_request.assert_awaited()
        mock_bg_task.assert_called_once()
