"""
Unit tests for src/storage/sqlite_repository.py
"""

import pytest
import asyncio
import tempfile
import os
from datetime import datetime, timedelta

from src.storage.sqlite_repository import SQLiteRepository
from src.domain.models import (
    ContentRecord,
    Schedule,
    ExecutionLog,
    TopicRequest,
)
from src.domain.enums import (
    Category,
    Difficulty,
    ExecutionStatus,
    ScheduleStatus,
    ContentStatus,
)


@pytest.fixture
async def repository():
    """Create a temporary SQLite repository for testing"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    repo = SQLiteRepository(db_path)
    await repo.initialize()

    yield repo

    await repo.close()
    os.unlink(db_path)


class TestSQLiteRepositoryInitialization:
    """Tests for repository initialization"""

    @pytest.mark.asyncio
    async def test_initialize_creates_tables(self):
        """Should create all required tables"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        repo = SQLiteRepository(db_path)
        await repo.initialize()

        # Verify tables exist by querying them
        conn = await repo._get_connection()
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row["name"] for row in await cursor.fetchall()}

        assert "content_records" in tables
        assert "schedules" in tables
        assert "execution_logs" in tables
        assert "topic_requests" in tables

        await repo.close()
        os.unlink(db_path)


class TestContentRecordOperations:
    """Tests for content record CRUD operations"""

    @pytest.mark.asyncio
    async def test_save_content(self, repository):
        """Should save content record and return with ID"""
        content = ContentRecord(
            title="Test Content",
            category=Category.NETWORK,
            difficulty=Difficulty.INTERMEDIATE,
            summary="Test summary",
            content="Test full content",
            tags=["tag1", "tag2"],
            author="TestUser",
        )

        saved = await repository.save_content(content)

        assert saved.id is not None
        assert saved.title == "Test Content"

    @pytest.mark.asyncio
    async def test_get_content(self, repository):
        """Should retrieve content by ID"""
        content = ContentRecord(
            title="Get Test",
            category=Category.ALGORITHM,
            summary="Summary",
            content="Content",
            author="User",
        )
        saved = await repository.save_content(content)

        retrieved = await repository.get_content(saved.id)

        assert retrieved is not None
        assert retrieved.id == saved.id
        assert retrieved.title == "Get Test"

    @pytest.mark.asyncio
    async def test_get_content_by_title(self, repository):
        """Should retrieve content by title"""
        content = ContentRecord(
            title="Unique Title",
            category=Category.DATABASE,
            summary="Summary",
            content="Content",
            author="User",
        )
        await repository.save_content(content)

        retrieved = await repository.get_content_by_title("Unique Title")

        assert retrieved is not None
        assert retrieved.title == "Unique Title"

    @pytest.mark.asyncio
    async def test_list_contents(self, repository):
        """Should list all contents"""
        for i in range(3):
            content = ContentRecord(
                title=f"Content {i}",
                category=Category.NETWORK,
                summary=f"Summary {i}",
                content=f"Content {i}",
                author="User",
            )
            await repository.save_content(content)

        contents = await repository.list_contents()

        assert len(contents) == 3


class TestExecutionLogOperations:
    """Tests for execution log CRUD operations"""

    @pytest.mark.asyncio
    async def test_save_execution_log(self, repository):
        """Should save execution log"""
        log = ExecutionLog(
            schedule_id=1,
            status=ExecutionStatus.PENDING,
        )

        saved = await repository.save_execution_log(log)

        assert saved.id is not None

    @pytest.mark.asyncio
    async def test_save_execution_log_with_duration(self, repository):
        """Should save execution log with duration_ms"""
        log = ExecutionLog(
            schedule_id=1,
            status=ExecutionStatus.SUCCESS,
            duration_ms=1500,
        )

        saved = await repository.save_execution_log(log)
        retrieved = await repository.get_execution_log(saved.id)

        assert retrieved.duration_ms == 1500

    @pytest.mark.asyncio
    async def test_update_execution_log_duration(self, repository):
        """Should update execution log with duration_ms"""
        log = ExecutionLog(
            schedule_id=1,
            status=ExecutionStatus.PENDING,
        )
        saved = await repository.save_execution_log(log)

        # Update with duration
        saved.status = ExecutionStatus.SUCCESS
        saved.duration_ms = 2500
        saved.completed_at = datetime.now()
        await repository.update_execution_log(saved)

        retrieved = await repository.get_execution_log(saved.id)

        assert retrieved.status == ExecutionStatus.SUCCESS
        assert retrieved.duration_ms == 2500

    @pytest.mark.asyncio
    async def test_get_execution_stats_includes_duration(self, repository):
        """Should include duration stats in execution statistics"""
        # Create logs with different durations
        for duration in [1000, 2000, 3000]:
            log = ExecutionLog(
                schedule_id=1,
                status=ExecutionStatus.SUCCESS,
                duration_ms=duration,
                completed_at=datetime.now(),
            )
            await repository.save_execution_log(log)

        stats = await repository.get_execution_stats()
        success_stats = stats.get(ExecutionStatus.SUCCESS.value, {})

        assert success_stats.get("avg_duration_ms") == 2000.0
        assert success_stats.get("min_duration_ms") == 1000
        assert success_stats.get("max_duration_ms") == 3000


class TestScheduleOperations:
    """Tests for schedule CRUD operations"""

    @pytest.mark.asyncio
    async def test_save_schedule(self, repository):
        """Should save schedule"""
        schedule = Schedule(
            time="07:00",
            status=ScheduleStatus.ACTIVE,
        )

        saved = await repository.save_schedule(schedule)

        assert saved.id is not None
        assert saved.time == "07:00"

    @pytest.mark.asyncio
    async def test_get_schedule_by_time(self, repository):
        """Should retrieve schedule by time"""
        schedule = Schedule(time="09:00")
        await repository.save_schedule(schedule)

        retrieved = await repository.get_schedule_by_time("09:00")

        assert retrieved is not None
        assert retrieved.time == "09:00"

    @pytest.mark.asyncio
    async def test_list_schedules_active_only(self, repository):
        """Should list only active schedules by default"""
        active = Schedule(time="07:00", status=ScheduleStatus.ACTIVE)
        paused = Schedule(time="19:00", status=ScheduleStatus.PAUSED)

        await repository.save_schedule(active)
        await repository.save_schedule(paused)

        schedules = await repository.list_schedules(status=ScheduleStatus.ACTIVE)

        assert len(schedules) == 1
        assert schedules[0].time == "07:00"


class TestTopicRequestOperations:
    """Tests for topic request CRUD operations"""

    @pytest.mark.asyncio
    async def test_save_topic_request(self, repository):
        """Should save topic request"""
        request = TopicRequest(
            topic="TCP/IP",
            requested_by="user123",
        )

        saved = await repository.save_topic_request(request)

        assert saved.id is not None
        assert saved.topic == "TCP/IP"

    @pytest.mark.asyncio
    async def test_get_pending_requests(self, repository):
        """Should return only pending requests"""
        pending = TopicRequest(topic="Topic 1", requested_by="user1")
        await repository.save_topic_request(pending)

        requests = await repository.get_pending_requests()

        assert len(requests) == 1
        assert requests[0].topic == "Topic 1"
