"""
Pytest configuration and fixtures for Daily-Bot tests
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
from unittest.mock import AsyncMock

import pytest

from src.domain.enums import Category, ContentStatus, Difficulty, ScheduleStatus
from src.domain.models import ContentRecord, GeneratedContent, Schedule


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings(monkeypatch):
    """Mock settings for tests"""
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "test-secret")
    monkeypatch.setenv("SLACK_APP_TOKEN", "xapp-test-token")
    monkeypatch.setenv("SLACK_CHANNEL_ID", "C12345678")
    monkeypatch.setenv("NOTION_API_KEY", "secret_test-key")
    monkeypatch.setenv("NOTION_DATABASE_ID", "test-db-id")
    monkeypatch.setenv("BOT_OWNER_NAME", "TestUser")
    monkeypatch.setenv("TIMEZONE", "Asia/Seoul")


@pytest.fixture
def mock_slack_client():
    """Create mock Slack client"""
    client = AsyncMock()
    client.chat_postMessage = AsyncMock(return_value={"ok": True, "ts": "1234567890.123456"})
    client.auth_test = AsyncMock(return_value={"ok": True})
    client.conversations_open = AsyncMock(return_value={"channel": {"id": "D12345678"}})
    return client


@pytest.fixture
def mock_notion_client():
    """Create mock Notion client"""
    client = AsyncMock()
    client.pages.create = AsyncMock(
        return_value={"id": "test-page-id", "url": "https://notion.so/test-page"}
    )
    client.databases.retrieve = AsyncMock(
        return_value={"id": "test-db-id", "data_sources": [{"id": "test-ds-id"}]}
    )
    # data_sources API
    client.data_sources = AsyncMock()
    client.data_sources.retrieve = AsyncMock(
        return_value={
            "properties": {
                "제목": {},
                "카테고리": {},
                "난이도": {},
                "태그": {},
                "작성일": {},
                "작성자": {},
                "상태": {},
            }
        }
    )
    client.data_sources.update = AsyncMock(return_value={})
    return client


@pytest.fixture
def sample_content():
    """Create sample content for tests"""
    return ContentRecord(
        id=1,
        title="TCP 3-way handshake",
        category=Category.NETWORK,
        difficulty=Difficulty.INTERMEDIATE,
        summary="TCP 연결 수립 과정을 설명합니다.",
        content="# TCP 3-way handshake\n\n상세 내용...",
        tags=["네트워크", "TCP", "프로토콜"],
        author="TestUser",
        status=ContentStatus.DRAFT,
    )


@pytest.fixture
def mock_repository():
    """ContentRepository with all methods mocked"""
    repo = AsyncMock()
    repo.initialize = AsyncMock()
    repo.close = AsyncMock()
    repo.save_content = AsyncMock(
        return_value=ContentRecord(
            id=1,
            title="Test Topic",
            category=Category.NETWORK,
            difficulty=Difficulty.INTERMEDIATE,
            summary="Test summary",
            content="Test summary",
            tags=["tag1"],
            author="TestUser",
            status=ContentStatus.DRAFT,
        )
    )
    repo.update_content = AsyncMock(
        return_value=ContentRecord(
            id=1,
            title="Test Topic",
            category=Category.NETWORK,
            difficulty=Difficulty.INTERMEDIATE,
            summary="Test summary",
            content="Test summary",
            tags=["tag1"],
            author="TestUser",
            status=ContentStatus.PUBLISHED,
        )
    )
    repo.get_content = AsyncMock(return_value=None)
    repo.get_used_topics = AsyncMock(return_value=[])
    repo.list_schedules = AsyncMock(return_value=[])
    repo.save_schedule = AsyncMock(
        return_value=Schedule(id=1, time="07:00", status=ScheduleStatus.ACTIVE)
    )
    repo.update_schedule = AsyncMock()
    repo.get_schedule_by_time = AsyncMock(return_value=None)
    repo.delete_schedule = AsyncMock(return_value=True)
    repo.save_execution_log = AsyncMock()
    repo.update_execution_log = AsyncMock()
    repo.list_execution_logs = AsyncMock(return_value=[])
    repo.get_content_count = AsyncMock(return_value=0)
    repo.get_execution_stats = AsyncMock(
        return_value={
            "success": {
                "count": 9,
                "total_attempts": 10,
                "avg_duration_ms": 10500,
                "min_duration_ms": 8000,
                "max_duration_ms": 15000,
            },
            "failed": {
                "count": 1,
                "total_attempts": 5,
                "avg_duration_ms": None,
                "min_duration_ms": None,
                "max_duration_ms": None,
            },
        }
    )
    repo.get_category_distribution = AsyncMock(return_value={"network": 3, "os": 2})
    repo.save_topic_request = AsyncMock()
    repo.mark_request_processed = AsyncMock()
    return repo


@pytest.fixture
def mock_generator():
    """ContentGenerator mocked"""
    gen = AsyncMock()
    gen.generate = AsyncMock(
        return_value=GeneratedContent(
            title="Test Topic",
            category=Category.NETWORK,
            difficulty=Difficulty.INTERMEDIATE,
            summary="Test summary",
            tags=["tag1"],
        )
    )
    gen.generate_random = AsyncMock(
        return_value=GeneratedContent(
            title="Random Topic",
            category=Category.OS,
            difficulty=Difficulty.BEGINNER,
            summary="Random summary",
            tags=["tag2"],
        )
    )
    gen.health_check = AsyncMock(return_value=True)
    return gen


@pytest.fixture
def mock_notion_adapter():
    """NotionAdapter mocked"""
    adapter = AsyncMock()
    adapter.create_content_page = AsyncMock(return_value=("page-id", "https://notion.so/page"))
    adapter.create_report_page = AsyncMock(
        return_value=("report-page-id", "https://notion.so/report")
    )
    adapter.health_check = AsyncMock(return_value=True)
    return adapter


@pytest.fixture
def mock_slack_adapter():
    """SlackAdapter mocked"""
    adapter = AsyncMock()
    adapter.send_content_notification = AsyncMock(return_value="1234567890.123456")
    adapter.send_error_notification = AsyncMock()
    adapter.send_report_notification = AsyncMock()
    adapter.send_status = AsyncMock()
    adapter.health_check = AsyncMock(return_value=True)
    return adapter
