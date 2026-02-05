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

## Setup & Run (Quick Start)

### Prerequisites

- Python 3.11+
- Node.js (Claude Code CLI 설치용)

```bash
python --version          # 3.11 이상 확인
npm install -g @anthropic-ai/claude-code
claude --version          # CLI 설치 확인
```

### 1. 클론 및 의존성 설치

```bash
git clone https://github.com/jeonjuho23/claude-daily.git
cd claude-daily
pip install -r requirements.txt
```

### 2. 외부 서비스 설정

**Slack App** (https://api.slack.com/apps)
1. Create New App > From scratch
2. **Socket Mode** 활성화 > App-Level Token 생성 (`xapp-`)
3. **OAuth & Permissions** > Bot Token Scopes: `chat:write`, `commands`, `app_mentions:read`
4. Install to Workspace > Bot Token 복사 (`xoxb-`)
5. **Slash Commands** > `/daily-bot` 등록 (Request URL은 Socket Mode라 불필요)
6. **Basic Information** > Signing Secret 복사
7. 발행할 채널에 봇 초대: `/invite @daily-bot`
8. 채널 ID 확인: 채널 우클릭 > 채널 세부정보 > 하단

**Notion Integration** (https://www.notion.so/my-integrations)
1. New integration > Internal integration > API Key 복사 (`secret_`)
2. 데이터베이스 페이지에서 `...` > 연결 > 생성한 integration 추가
3. 데이터베이스 URL에서 ID 추출: `notion.so/{DATABASE_ID}?v=...`

### 3. 환경 변수 설정

```bash
cp .env.example .env
```

`.env` 편집:
```env
SLACK_BOT_TOKEN=xoxb-실제토큰
SLACK_SIGNING_SECRET=실제시크릿
SLACK_APP_TOKEN=xapp-실제토큰
SLACK_CHANNEL_ID=C실제채널ID
NOTION_API_KEY=secret_실제키
NOTION_DATABASE_ID=실제데이터베이스ID
BOT_OWNER_NAME=본인이름
DEFAULT_SCHEDULE_TIME=07:00
TIMEZONE=Asia/Seoul
```

### 4. 실행

```bash
python main.py
```

시작 시 health check 결과 표시:
```
Slack API: OK
Notion API: OK
Claude Code CLI: OK
Daily-Bot is running. Press Ctrl+C to stop.
```

3개 모두 OK면 `DEFAULT_SCHEDULE_TIME`에 자동 실행. `/daily-bot now`으로 즉시 테스트 가능.

이 프로세스는 **상시 실행(데몬)** 형태. APScheduler가 설정 시간에 자동으로 콘텐츠 생성/발행. Ctrl+C로 종료.

### 5. 백그라운드 실행 (터미널 꺼도 유지)

**Windows (PowerShell):**
```powershell
Start-Process python -ArgumentList "main.py" -WorkingDirectory "C:\path\to\daily-bot" -WindowStyle Hidden
```

**Linux (systemd):**
```bash
# /etc/systemd/system/daily-bot.service
[Unit]
Description=Daily-Bot CS Knowledge Sharing
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/daily-bot
ExecStart=/path/to/venv/bin/python main.py
Restart=always
RestartSec=10
Environment=PYTHONIOENCODING=utf-8

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl enable daily-bot && sudo systemctl start daily-bot
```

### 6. 동작 확인

- 로그: `logs/` 디렉토리에 자동 생성
- Slack에서 `/daily-bot status` 명령으로 상태 확인
- `/daily-bot now` 로 즉시 실행 테스트

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
