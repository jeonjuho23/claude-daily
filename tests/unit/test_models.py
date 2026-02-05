"""
Unit tests for domain models
"""

import pytest
from datetime import datetime

from src.domain.models import (
    ContentRecord,
    Schedule,
    ExecutionLog,
    TopicRequest,
    ReportData,
    BotStatus,
    GeneratedContent,
)
from src.domain.enums import (
    Category,
    Difficulty,
    ExecutionStatus,
    ScheduleStatus,
    ReportType,
    ContentStatus,
)


class TestContentRecord:
    """Tests for ContentRecord model"""
    
    def test_create_content_record(self):
        """Test creating a content record"""
        content = ContentRecord(
            title="Test Title",
            category=Category.NETWORK,
            summary="Test summary",
            content="Test content",
            author="TestUser",
        )
        
        assert content.title == "Test Title"
        assert content.category == Category.NETWORK
        assert content.difficulty == Difficulty.INTERMEDIATE  # default
        assert content.status == ContentStatus.DRAFT  # default
        assert content.tags == []  # default
    
    def test_content_with_all_fields(self):
        """Test content record with all fields"""
        content = ContentRecord(
            id=1,
            title="Full Test",
            category=Category.ALGORITHM,
            difficulty=Difficulty.ADVANCED,
            summary="Full summary",
            content="Full content",
            tags=["tag1", "tag2"],
            notion_page_id="page-123",
            notion_url="https://notion.so/page",
            slack_ts="1234567890.123456",
            author="Author",
            status=ContentStatus.PUBLISHED,
        )
        
        assert content.id == 1
        assert content.notion_page_id == "page-123"
        assert len(content.tags) == 2


class TestSchedule:
    """Tests for Schedule model"""
    
    def test_create_schedule(self):
        """Test creating a schedule"""
        schedule = Schedule(
            time="07:00",
        )
        
        assert schedule.time == "07:00"
        assert schedule.status == ScheduleStatus.ACTIVE
    
    def test_schedule_with_status(self):
        """Test schedule with specific status"""
        schedule = Schedule(
            time="19:00",
            status=ScheduleStatus.PAUSED,
        )
        
        assert schedule.status == ScheduleStatus.PAUSED


class TestExecutionLog:
    """Tests for ExecutionLog model"""
    
    def test_create_execution_log(self):
        """Test creating an execution log"""
        log = ExecutionLog(
            schedule_id=1,
            status=ExecutionStatus.PENDING,
        )
        
        assert log.schedule_id == 1
        assert log.status == ExecutionStatus.PENDING
        assert log.attempt_count == 0
    
    def test_execution_log_with_error(self):
        """Test execution log with error"""
        log = ExecutionLog(
            schedule_id=1,
            status=ExecutionStatus.FAILED,
            attempt_count=5,
            error_message="Connection timeout",
        )
        
        assert log.status == ExecutionStatus.FAILED
        assert log.error_message == "Connection timeout"


class TestReportData:
    """Tests for ReportData model"""
    
    def test_create_weekly_report(self):
        """Test creating weekly report"""
        report = ReportData(
            report_type=ReportType.WEEKLY,
            period_start=datetime(2024, 1, 1),
            period_end=datetime(2024, 1, 7),
            total_count=5,
            success_count=4,
            failed_count=1,
        )
        
        assert report.report_type == ReportType.WEEKLY
        assert report.total_count == 5
        assert report.category_distribution == {}


class TestDifficulty:
    """Tests for Difficulty enum"""
    
    def test_difficulty_korean(self):
        """Test Korean difficulty names"""
        assert Difficulty.BEGINNER.korean == "초급"
        assert Difficulty.INTERMEDIATE.korean == "중급"
        assert Difficulty.ADVANCED.korean == "고급"


class TestBotStatus:
    """Tests for BotStatus model"""
    
    def test_default_bot_status(self):
        """Test default bot status"""
        status = BotStatus()
        
        assert status.is_running == True
        assert status.is_paused == False
        assert status.total_generated == 0
        assert status.active_schedules == []
