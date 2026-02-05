# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Daily-Bot is an automated CS knowledge sharing bot for developers. It generates daily CS learning content (summary-only) using Claude Code CLI and publishes to Slack (announcements) and Notion (callout summary). Written in Python 3.11+ with async/await patterns throughout. Uses Notion API 2025-09-03 (data_sources model) via notion-client 2.7.0+.

## Commands

```bash
# Testing
pytest                          # Run all tests
pytest tests/unit/              # Run unit tests only
pytest tests/unit/test_models.py -v  # Run specific test file
pytest -k "test_name"           # Run tests matching pattern

# Code Quality
black .                         # Format code
ruff check .                    # Lint code
mypy .                          # Type checking

# Run Application
python main.py                  # Start the bot
```

## Architecture

```
main.py                         # Entry point: component initialization, lifecycle management
├── src/core/engine.py          # CoreEngine: central orchestrator, scheduling, workflow
├── src/generators/
│   ├── base.py                 # Abstract ContentGenerator interface
│   └── claude_code_generator.py # Executes `claude --print` CLI, parses JSON output
├── src/integrations/
│   ├── slack/adapter.py        # SlackAdapter: messages, notifications
│   ├── slack/command_handler.py # CommandHandler: /daily-bot slash commands
│   └── notion/adapter.py       # NotionAdapter: data_sources API, callout pages
├── src/storage/
│   ├── base.py                 # Abstract ContentRepository interface
│   └── sqlite_repository.py    # Async SQLite with aiosqlite
├── src/reports/generator.py    # Weekly/monthly statistics reports
├── src/errors/handler.py       # Retry logic with exponential backoff
└── src/utils/                  # Logging (structlog), datetime utilities
```

## Key Patterns

- **Adapter Pattern**: SlackAdapter, NotionAdapter wrap external APIs
- **Repository Pattern**: Abstract storage interface with SQLite implementation
- **Strategy Pattern**: Pluggable content generators via ContentGenerator interface
- **All I/O is async**: Uses asyncio, aiosqlite, async Slack/Notion clients

## Configuration

- `config/settings.py` - Pydantic-based settings from environment variables
- `config/topics.py` - 240+ CS topics across 12 categories with difficulty weights
- `.env` - Required: SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET, SLACK_APP_TOKEN, SLACK_CHANNEL_ID, NOTION_API_KEY, NOTION_DATABASE_ID

## Domain Models

Located in `src/domain/models.py` (all use `model_config = ConfigDict(...)`):
- `ContentRecord` - Generated content with metadata
- `Schedule` - Execution schedule configuration
- `ExecutionLog` - Execution tracking with error info and duration_ms
- `GeneratedContent` - Output from Claude Code generator (summary-only, content field optional)

Enums in `src/domain/enums.py`: Category (12 types), Difficulty (beginner/intermediate/advanced), ExecutionStatus, ScheduleStatus

## Content Generation Flow

1. CoreEngine triggers scheduled execution
2. ClaudeCodeGenerator selects random topic (weighted by difficulty: 25% beginner, 50% intermediate, 25% advanced)
3. Generator runs `claude --print` with prompt template (summary-only: title, summary, tags)
4. Parses JSON response into GeneratedContent (~10s, no truncation risk)
5. Saves to SQLite, posts summary to Slack, creates Notion page with callout block
6. On failure: ErrorHandler retries 5 times with exponential backoff (5, 10, 15, 20, 25 min intervals)

## Notion Integration

- Uses API version `2025-09-03` with `data_sources` model (not legacy `database_id`)
- `_get_data_source_id()` resolves data_source_id from database on first call
- `_ensure_database_schema()` auto-creates missing properties via `data_sources.update`
- Pages created with `parent: {"type": "data_source_id", "data_source_id": ...}`
- Properties: 제목(title), 카테고리(select), 난이도(select), 태그(multi_select), 작성일(date), 작성자(rich_text), 상태(select)

## Slack Commands

`/daily-bot <command>`: help, status, time, add, remove, list, pause, resume, now, request

## Database

SQLite with tables: content_records, schedules, execution_logs (with duration_ms), topic_requests. Schema managed in sqlite_repository.py.
