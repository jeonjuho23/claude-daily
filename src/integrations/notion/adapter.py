"""
Notion integration adapter
Handles all Notion API interactions (API version 2025-09-03 with data_sources)
"""

import asyncio
import re
from datetime import datetime
from typing import Any

from notion_client import AsyncClient
from notion_client.errors import APIResponseError

from config.settings import settings
from config.topics import get_category_name
from src.domain.enums import Category, Difficulty
from src.domain.models import ContentRecord, ReportData
from src.utils.datetime_utils import format_datetime
from src.utils.logger import get_logger
from src.utils.rate_limiter import AsyncRateLimiter

logger = get_logger(__name__)


class NotionAdapter:
    """
    Adapter for Notion API interactions

    Uses Notion API 2025-09-03 with data_sources model.
    Pages are created under data_source_id instead of database_id.
    """

    def __init__(self, api_key: str | None = None):
        self.client = AsyncClient(auth=api_key or settings.notion_api_key)
        self.database_id = settings.notion_database_id
        self._data_source_id: str | None = None
        self._schema_initialized = False
        self._schema_lock = asyncio.Lock()
        self._rate_limiter = AsyncRateLimiter(rate=settings.notion_rate_limit, period=1.0, burst=2)

    async def _get_data_source_id(self) -> str:
        """Get the data_source_id from the database"""
        if self._data_source_id:
            return self._data_source_id

        async with self._rate_limiter:
            db = await self.client.databases.retrieve(database_id=self.database_id)
        data_sources = db.get("data_sources", [])
        if not data_sources:
            raise RuntimeError(
                f"No data sources found for database {self.database_id}. "
                "Please check that the database exists and the integration has access."
            )
        self._data_source_id = data_sources[0]["id"]
        logger.info("Resolved data source", data_source_id=self._data_source_id)
        return self._data_source_id

    async def _ensure_database_schema(self) -> None:
        """Ensure the data source has all required properties"""
        if self._schema_initialized:
            return

        async with self._schema_lock:
            if self._schema_initialized:
                return

            try:
                ds_id = await self._get_data_source_id()
                async with self._rate_limiter:
                    ds = await self.client.data_sources.retrieve(data_source_id=ds_id)
                existing = set(ds.get("properties", {}).keys())

                required_properties = {}
                schema = {
                    "카테고리": {"select": {"options": []}},
                    "난이도": {"select": {"options": []}},
                    "태그": {"multi_select": {"options": []}},
                    "작성일": {"date": {}},
                    "작성자": {"rich_text": {}},
                    "상태": {"select": {"options": []}},
                }

                for name, config in schema.items():
                    if name not in existing:
                        required_properties[name] = config

                # Check if title property needs renaming (default "이름" → "제목")
                if "이름" in existing and "제목" not in existing:
                    required_properties["이름"] = {"name": "제목"}

                if required_properties:
                    async with self._rate_limiter:
                        await self.client.data_sources.update(
                            data_source_id=ds_id,
                            properties=required_properties,
                        )
                    logger.info(
                        "Data source schema updated",
                        added_properties=list(required_properties.keys()),
                    )

                self._schema_initialized = True

            except APIResponseError as e:
                logger.warning("Failed to ensure database schema", error=str(e))

    async def create_content_page(
        self,
        content: ContentRecord,
        database_id: str | None = None,
    ) -> tuple[str, str]:
        """
        Create a new page in Notion for content

        Args:
            content: Content record to create page for
            database_id: Override database ID (unused, kept for compatibility)

        Returns:
            Tuple of (page_id, page_url)
        """
        await self._ensure_database_schema()
        ds_id = await self._get_data_source_id()

        # Get category display name
        category_value = (
            content.category.value if isinstance(content.category, Category) else content.category
        )
        category_name = get_category_name(category_value, settings.language)

        # Get difficulty display name
        difficulty_value = (
            content.difficulty.value
            if isinstance(content.difficulty, Difficulty)
            else content.difficulty
        )
        difficulty_name = (
            content.difficulty.korean if hasattr(content.difficulty, "korean") else difficulty_value
        )

        try:
            properties = {
                "제목": {"title": [{"text": {"content": content.title}}]},
                "카테고리": {"select": {"name": category_name}},
                "난이도": {"select": {"name": difficulty_name}},
                "태그": {"multi_select": [{"name": tag} for tag in content.tags[:10]]},
                "작성일": {
                    "date": {
                        "start": (
                            content.created_at.strftime("%Y-%m-%d")
                            if content.created_at
                            else datetime.now().strftime("%Y-%m-%d")
                        )
                    }
                },
                "작성자": {"rich_text": [{"text": {"content": content.author}}]},
                "상태": {"select": {"name": "발행됨"}},
            }

            children = [
                {
                    "type": "callout",
                    "callout": {
                        "rich_text": [
                            {"type": "text", "text": {"content": content.summary[:2000]}}
                        ],
                        "icon": {"type": "emoji", "emoji": "💡"},
                    },
                }
            ]

            async with self._rate_limiter:
                response = await self.client.pages.create(
                    parent={"type": "data_source_id", "data_source_id": ds_id},
                    properties=properties,
                    children=children,
                )

            page_id = response["id"]
            page_url = response["url"]

            logger.info(
                "Notion page created",
                page_id=page_id,
                title=content.title,
            )

            return page_id, page_url

        except APIResponseError as e:
            logger.error(
                "Failed to create Notion page",
                title=content.title,
                error=str(e),
            )
            raise

    async def create_report_page(
        self,
        report: ReportData,
        database_id: str | None = None,
    ) -> tuple[str, str]:
        """
        Create a report page in Notion

        Args:
            report: Report data
            database_id: Override database ID (unused, kept for compatibility)

        Returns:
            Tuple of (page_id, page_url)
        """
        await self._ensure_database_schema()
        ds_id = await self._get_data_source_id()

        report_type_ko = "주간" if report.report_type == "weekly" else "월간"
        title = f"[{report_type_ko} 리포트] {format_datetime(report.period_start, False)} ~ {format_datetime(report.period_end, False)}"

        summary_lines = [
            f"총 발송: {report.total_count}건",
            f"성공: {report.success_count}건 / 실패: {report.failed_count}건",
            f"재시도: {report.retry_count}건",
        ]
        if report.avg_duration_ms:
            summary_lines.append(f"평균 실행시간: {report.avg_duration_ms:.0f}ms")

        try:
            properties = {
                "제목": {"title": [{"text": {"content": title}}]},
                "카테고리": {"select": {"name": "리포트"}},
                "난이도": {"select": {"name": "-"}},
                "태그": {
                    "multi_select": [
                        {"name": report_type_ko},
                        {"name": "통계"},
                    ]
                },
                "작성일": {
                    "date": {
                        "start": (
                            report.generated_at.strftime("%Y-%m-%d")
                            if report.generated_at
                            else datetime.now().strftime("%Y-%m-%d")
                        )
                    }
                },
                "작성자": {"rich_text": [{"text": {"content": "Daily-Bot"}}]},
                "상태": {"select": {"name": "발행됨"}},
            }

            children = [
                {
                    "type": "heading_2",
                    "heading_2": {"rich_text": [{"type": "text", "text": {"content": "요약"}}]},
                },
                {
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"기간: {format_datetime(report.period_start, False)} ~ {format_datetime(report.period_end, False)}"
                                },
                            }
                        ]
                    },
                },
                {
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": f"총 발송: {report.total_count}건"},
                            }
                        ]
                    },
                },
                {
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [
                            {"type": "text", "text": {"content": f"성공: {report.success_count}건"}}
                        ]
                    },
                },
                {
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [
                            {"type": "text", "text": {"content": f"실패: {report.failed_count}건"}}
                        ]
                    },
                },
                {
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [
                            {"type": "text", "text": {"content": f"재시도: {report.retry_count}건"}}
                        ]
                    },
                },
            ]

            if report.avg_duration_ms:
                children.append(
                    {
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": f"평균 실행시간: {report.avg_duration_ms:.0f}ms (최소: {report.min_duration_ms}ms, 최대: {report.max_duration_ms}ms)"
                                    },
                                }
                            ]
                        },
                    }
                )

            children.append({"type": "divider", "divider": {}})

            if report.category_distribution:
                children.append(
                    {
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{"type": "text", "text": {"content": "카테고리별 분포"}}]
                        },
                    }
                )

                for cat, count in sorted(
                    report.category_distribution.items(), key=lambda x: x[1], reverse=True
                ):
                    cat_name = get_category_name(cat, settings.language)
                    children.append(
                        {
                            "type": "bulleted_list_item",
                            "bulleted_list_item": {
                                "rich_text": [
                                    {"type": "text", "text": {"content": f"{cat_name}: {count}건"}}
                                ]
                            },
                        }
                    )

                children.append({"type": "divider", "divider": {}})

            if report.uncovered_categories:
                children.append(
                    {
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{"type": "text", "text": {"content": "미다룬 카테고리"}}]
                        },
                    }
                )

                uncovered_text = ", ".join(
                    [
                        get_category_name(cat, settings.language)
                        for cat in report.uncovered_categories
                    ]
                )
                children.append(
                    {
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": uncovered_text}}]
                        },
                    }
                )

            async with self._rate_limiter:
                response = await self.client.pages.create(
                    parent={"type": "data_source_id", "data_source_id": ds_id},
                    properties=properties,
                    children=children,
                )

            page_id = response["id"]
            page_url = response["url"]

            logger.info(
                "Report page created",
                page_id=page_id,
                report_type=report.report_type,
            )

            return page_id, page_url

        except APIResponseError as e:
            logger.error(
                "Failed to create report page",
                error=str(e),
            )
            raise

    def _markdown_to_blocks(self, markdown: str) -> list[dict[str, Any]]:
        """Convert markdown content to Notion blocks"""
        blocks = []
        lines = markdown.split("\n")

        i = 0
        code_block = None
        code_language = ""

        while i < len(lines):
            line = lines[i]

            # Code block
            if line.startswith("```"):
                if code_block is None:
                    code_language = line[3:].strip() or "plain text"
                    code_block = []
                else:
                    blocks.append(
                        {
                            "type": "code",
                            "code": {
                                "rich_text": [
                                    {"type": "text", "text": {"content": "\n".join(code_block)}}
                                ],
                                "language": self._map_language(code_language),
                            },
                        }
                    )
                    code_block = None
                i += 1
                continue

            if code_block is not None:
                code_block.append(line)
                i += 1
                continue

            # Headers
            if line.startswith("# "):
                blocks.append(
                    {
                        "type": "heading_1",
                        "heading_1": {
                            "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                        },
                    }
                )
            elif line.startswith("## "):
                blocks.append(
                    {
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{"type": "text", "text": {"content": line[3:]}}]
                        },
                    }
                )
            elif line.startswith("### "):
                blocks.append(
                    {
                        "type": "heading_3",
                        "heading_3": {
                            "rich_text": [{"type": "text", "text": {"content": line[4:]}}]
                        },
                    }
                )
            # Bullet list
            elif line.startswith("- ") or line.startswith("* "):
                blocks.append(
                    {
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": self._parse_inline_formatting(line[2:])
                        },
                    }
                )
            # Numbered list
            elif num_match := re.match(r"^(\d+)\.\s+(.*)", line):
                blocks.append(
                    {
                        "type": "numbered_list_item",
                        "numbered_list_item": {
                            "rich_text": self._parse_inline_formatting(num_match.group(2))
                        },
                    }
                )
            # Quote
            elif line.startswith("> "):
                blocks.append(
                    {
                        "type": "quote",
                        "quote": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]},
                    }
                )
            # Divider
            elif line.strip() in ["---", "***", "___"]:
                blocks.append({"type": "divider", "divider": {}})
            # Empty line
            elif not line.strip():
                pass
            # Regular paragraph
            else:
                blocks.append(
                    {
                        "type": "paragraph",
                        "paragraph": {"rich_text": self._parse_inline_formatting(line)},
                    }
                )

            i += 1

        return blocks

    def _parse_inline_formatting(self, text: str) -> list[dict[str, Any]]:
        """Parse inline markdown formatting"""
        return [{"type": "text", "text": {"content": text}}]

    def _map_language(self, lang: str) -> str:
        """Map language name to Notion's supported language codes"""
        mapping = {
            "python": "python",
            "py": "python",
            "javascript": "javascript",
            "js": "javascript",
            "typescript": "typescript",
            "ts": "typescript",
            "java": "java",
            "go": "go",
            "rust": "rust",
            "c": "c",
            "cpp": "c++",
            "c++": "c++",
            "csharp": "c#",
            "c#": "c#",
            "sql": "sql",
            "bash": "bash",
            "shell": "shell",
            "json": "json",
            "yaml": "yaml",
            "html": "html",
            "css": "css",
            "kotlin": "kotlin",
            "swift": "swift",
            "ruby": "ruby",
            "php": "php",
        }
        return mapping.get(lang.lower(), "plain text")

    async def health_check(self) -> bool:
        """Check Notion API connection"""
        try:
            await self.client.databases.retrieve(database_id=self.database_id)
            return True
        except APIResponseError as e:
            logger.warning("Notion health check failed", error=str(e))
            return False
