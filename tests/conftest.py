"""
Pytest configuration and fixtures for Daily-Bot tests
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock


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
    client.pages.create = AsyncMock(return_value={
        "id": "test-page-id",
        "url": "https://notion.so/test-page"
    })
    client.databases.retrieve = AsyncMock(return_value={"id": "test-db-id"})
    return client


@pytest.fixture
def sample_content():
    """Create sample content for tests"""
    from src.domain.models import ContentRecord
    from src.domain.enums import Category, Difficulty, ContentStatus
    
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
