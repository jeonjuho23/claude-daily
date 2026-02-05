"""
Integration tests for src/integrations/notion/adapter.py
"""

import asyncio
from datetime import datetime
from unittest.mock import patch

import pytest

from src.domain.enums import Category, ContentStatus, Difficulty, ReportType
from src.domain.models import ContentRecord, ReportData
from src.integrations.notion.adapter import NotionAdapter


@pytest.fixture
def notion_adapter(mock_settings, mock_notion_client):
    """Create NotionAdapter with mocked client"""
    from config.settings import get_settings

    get_settings.cache_clear()

    with patch("src.integrations.notion.adapter.AsyncClient") as MockClient:
        MockClient.return_value = mock_notion_client
        adapter = NotionAdapter()
        adapter.client = mock_notion_client
        yield adapter


@pytest.fixture
def sample_content():
    return ContentRecord(
        id=1,
        title="TCP 3-way handshake",
        category=Category.NETWORK,
        difficulty=Difficulty.INTERMEDIATE,
        summary="TCP 연결 수립 과정을 설명합니다.",
        content="TCP 연결 수립 과정을 설명합니다.",
        tags=["네트워크", "TCP"],
        author="TestUser",
        status=ContentStatus.DRAFT,
    )


@pytest.fixture
def sample_report():
    return ReportData(
        report_type=ReportType.WEEKLY,
        period_start=datetime(2026, 1, 27),
        period_end=datetime(2026, 2, 2),
        total_count=7,
        success_count=6,
        failed_count=1,
        retry_count=2,
        category_distribution={"network": 3, "os": 2, "algorithm": 1},
        uncovered_categories=["security", "devops"],
        avg_duration_ms=10500.0,
        min_duration_ms=8000,
        max_duration_ms=15000,
        generated_at=datetime(2026, 2, 3),
    )


class TestGetDataSourceId:
    @pytest.mark.asyncio
    async def test_retrieves_from_database(self, notion_adapter, mock_notion_client):
        ds_id = await notion_adapter._get_data_source_id()
        assert ds_id == "test-ds-id"
        mock_notion_client.databases.retrieve.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_caches_result(self, notion_adapter, mock_notion_client):
        await notion_adapter._get_data_source_id()
        await notion_adapter._get_data_source_id()
        # Should only call once due to caching
        mock_notion_client.databases.retrieve.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_raises_when_no_sources(self, notion_adapter, mock_notion_client):
        mock_notion_client.databases.retrieve.return_value = {
            "id": "test-db-id",
            "data_sources": [],
        }
        with pytest.raises(RuntimeError, match="No data sources"):
            await notion_adapter._get_data_source_id()


class TestEnsureDatabaseSchema:
    @pytest.mark.asyncio
    async def test_skips_when_initialized(self, notion_adapter):
        notion_adapter._schema_initialized = True
        await notion_adapter._ensure_database_schema()
        # Should not make any API calls
        notion_adapter.client.data_sources.retrieve.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_creates_missing_properties(self, notion_adapter, mock_notion_client):
        # Only has 제목, missing others
        mock_notion_client.data_sources.retrieve.return_value = {"properties": {"제목": {}}}
        await notion_adapter._ensure_database_schema()
        mock_notion_client.data_sources.update.assert_awaited_once()
        call_kwargs = mock_notion_client.data_sources.update.call_args.kwargs
        assert "카테고리" in call_kwargs["properties"]

    @pytest.mark.asyncio
    async def test_skips_existing_properties(self, notion_adapter, mock_notion_client):
        # All properties already exist
        await notion_adapter._ensure_database_schema()
        # update should not be called since all required props exist
        mock_notion_client.data_sources.update.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_concurrent_schema_initialization(self, notion_adapter, mock_notion_client):
        """Two concurrent calls should only trigger one actual schema check"""
        await asyncio.gather(
            notion_adapter._ensure_database_schema(),
            notion_adapter._ensure_database_schema(),
        )
        # data_sources.retrieve should be called exactly once (second call sees _schema_initialized)
        mock_notion_client.data_sources.retrieve.assert_awaited_once()


class TestCreateContentPage:
    @pytest.mark.asyncio
    async def test_success_returns_id_and_url(self, notion_adapter, sample_content):
        page_id, url = await notion_adapter.create_content_page(sample_content)
        assert page_id == "test-page-id"
        assert url == "https://notion.so/test-page"

    @pytest.mark.asyncio
    async def test_correct_properties(self, notion_adapter, sample_content, mock_notion_client):
        await notion_adapter.create_content_page(sample_content)
        call_kwargs = mock_notion_client.pages.create.call_args.kwargs
        props = call_kwargs["properties"]
        assert "제목" in props
        assert "카테고리" in props
        assert "난이도" in props
        assert "태그" in props

    @pytest.mark.asyncio
    async def test_callout_block_summary(self, notion_adapter, sample_content, mock_notion_client):
        await notion_adapter.create_content_page(sample_content)
        call_kwargs = mock_notion_client.pages.create.call_args.kwargs
        children = call_kwargs["children"]
        assert children[0]["type"] == "callout"
        callout_text = children[0]["callout"]["rich_text"][0]["text"]["content"]
        assert callout_text == sample_content.summary

    @pytest.mark.asyncio
    async def test_truncates_summary_to_2000(self, notion_adapter, mock_notion_client):
        long_content = ContentRecord(
            id=2,
            title="Long Content",
            category=Category.NETWORK,
            difficulty=Difficulty.INTERMEDIATE,
            summary="x" * 3000,
            content="x" * 3000,
            tags=[],
            author="TestUser",
            status=ContentStatus.DRAFT,
        )
        await notion_adapter.create_content_page(long_content)
        call_kwargs = mock_notion_client.pages.create.call_args.kwargs
        children = call_kwargs["children"]
        callout_text = children[0]["callout"]["rich_text"][0]["text"]["content"]
        assert len(callout_text) == 2000

    @pytest.mark.asyncio
    async def test_uses_data_source_parent(
        self, notion_adapter, sample_content, mock_notion_client
    ):
        await notion_adapter.create_content_page(sample_content)
        call_kwargs = mock_notion_client.pages.create.call_args.kwargs
        parent = call_kwargs["parent"]
        assert parent["type"] == "data_source_id"
        assert parent["data_source_id"] == "test-ds-id"


class TestCreateReportPage:
    @pytest.mark.asyncio
    async def test_success(self, notion_adapter, sample_report):
        page_id, url = await notion_adapter.create_report_page(sample_report)
        assert page_id == "test-page-id"
        assert url == "https://notion.so/test-page"

    @pytest.mark.asyncio
    async def test_includes_duration_stats(self, notion_adapter, sample_report, mock_notion_client):
        await notion_adapter.create_report_page(sample_report)
        call_kwargs = mock_notion_client.pages.create.call_args.kwargs
        children = call_kwargs["children"]
        content_str = str(children)
        assert "10500" in content_str  # avg_duration_ms


class TestMarkdownToBlocks:
    def test_headers(self, notion_adapter):
        md = "# H1\n## H2\n### H3"
        blocks = notion_adapter._markdown_to_blocks(md)
        assert len(blocks) == 3
        assert blocks[0]["type"] == "heading_1"
        assert blocks[1]["type"] == "heading_2"
        assert blocks[2]["type"] == "heading_3"

    def test_lists_and_quotes(self, notion_adapter):
        md = "- bullet\n1. numbered\n> quote"
        blocks = notion_adapter._markdown_to_blocks(md)
        assert len(blocks) == 3
        assert blocks[0]["type"] == "bulleted_list_item"
        assert blocks[1]["type"] == "numbered_list_item"
        assert blocks[2]["type"] == "quote"

    def test_code_block(self, notion_adapter):
        md = "```python\nprint('hello')\n```"
        blocks = notion_adapter._markdown_to_blocks(md)
        assert len(blocks) == 1
        assert blocks[0]["type"] == "code"
        assert blocks[0]["code"]["language"] == "python"
        assert "print('hello')" in blocks[0]["code"]["rich_text"][0]["text"]["content"]

    def test_mixed_content(self, notion_adapter):
        md = "# Title\n\nParagraph text\n\n- item1\n- item2\n\n---\n\n> quote"
        blocks = notion_adapter._markdown_to_blocks(md)
        types = [b["type"] for b in blocks]
        assert types[0] == "heading_1"
        assert types[1] == "paragraph"
        assert types[2] == "bulleted_list_item"
        assert types[3] == "bulleted_list_item"
        assert types[4] == "divider"
        assert types[5] == "quote"

    def test_empty_markdown(self, notion_adapter):
        blocks = notion_adapter._markdown_to_blocks("")
        assert blocks == []

    def test_multidigit_numbered_list(self, notion_adapter):
        blocks = notion_adapter._markdown_to_blocks("10. Tenth item\n25. Twenty-fifth item")
        assert len(blocks) == 2
        assert blocks[0]["type"] == "numbered_list_item"
        assert blocks[1]["type"] == "numbered_list_item"
        text_0 = blocks[0]["numbered_list_item"]["rich_text"][0]["text"]["content"]
        text_1 = blocks[1]["numbered_list_item"]["rich_text"][0]["text"]["content"]
        assert text_0 == "Tenth item"
        assert text_1 == "Twenty-fifth item"


class TestMapLanguage:
    def test_known_languages(self, notion_adapter):
        assert notion_adapter._map_language("python") == "python"
        assert notion_adapter._map_language("py") == "python"
        assert notion_adapter._map_language("js") == "javascript"
        assert notion_adapter._map_language("cpp") == "c++"
        assert notion_adapter._map_language("typescript") == "typescript"

    def test_unknown_language_returns_plain_text(self, notion_adapter):
        assert notion_adapter._map_language("unknown_lang") == "plain text"
        assert notion_adapter._map_language("xyz") == "plain text"


class TestNotionHealthCheck:
    @pytest.mark.asyncio
    async def test_success(self, notion_adapter, mock_notion_client):
        result = await notion_adapter.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_failure(self, notion_adapter, mock_notion_client):
        from unittest.mock import MagicMock

        from notion_client.errors import APIResponseError

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_response.json.return_value = {"message": "Not found", "code": "not_found"}

        mock_notion_client.databases.retrieve.side_effect = APIResponseError(
            response=mock_response, message="Not found", code="not_found"
        )
        result = await notion_adapter.health_check()
        assert result is False
