# Daily-Bot 아키텍처 설계 문서

## 1. 프로젝트 개요

### 1.1 목적
매일 정해진 시간에 Claude Code를 활용하여 CS 지식 및 개발 방법론 콘텐츠를 자동 생성하고, Slack 채널에 요약을 공유하는 자동화 서비스. Notion 연동은 선택 사항으로, 설정 시 콘텐츠 페이지를 자동 생성합니다.

### 1.2 주요 기능
- 스케줄 기반 자동 콘텐츠 생성 및 발송
- Slack 명령어를 통한 설정 관리
- Notion 데이터베이스 연동
- 주간/월간 통계 리포트 생성
- 에러 알림 및 재시도 로직

### 1.3 사용 환경
- 사용자: 4명 (각자 독립적으로 운영)
- OS: Windows 11 / macOS 혼합
- 인증: 각 팀원이 Claude Pro/Max 구독 보유

---

## 2. 시스템 아키텍처

### 2.1 전체 구조

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              User's Local PC                                │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                         Daily-Bot Application                         │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │  │
│  │  │  Scheduler  │  │   Command   │  │   Report    │  │    Error    │   │  │
│  │  │   Service   │  │   Handler   │  │  Generator  │  │   Handler   │   │  │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘   │  │
│  │         │                │                │                │          │  │
│  │         └────────────────┴────────────────┴────────────────┘          │  │
│  │                                   │                                    │  │
│  │                          ┌────────▼────────┐                          │  │
│  │                          │   Core Engine   │                          │  │
│  │                          │  (Orchestrator) │                          │  │
│  │                          └────────┬────────┘                          │  │
│  │                                   │                                    │  │
│  │         ┌─────────────────────────┼─────────────────────────┐         │  │
│  │         │                         │                         │         │  │
│  │  ┌──────▼──────┐  ┌───────────────▼───────────────┐  ┌──────▼──────┐  │  │
│  │  │   Content   │  │        Integration Layer       │  │   Storage   │  │  │
│  │  │  Generator  │  │  ┌─────────┐  ┌────────────┐  │  │    Layer    │  │  │
│  │  │ (Interface) │  │  │  Slack  │  │   Notion   │  │  │ (Interface) │  │  │
│  │  └──────┬──────┘  │  │ Adapter │  │  Adapter   │  │  └──────┬──────┘  │  │
│  │         │         │  └────┬────┘  └─────┬──────┘  │         │         │  │
│  │         │         └───────┼─────────────┼─────────┘         │         │  │
│  └─────────┼─────────────────┼─────────────┼───────────────────┼─────────┘  │
│            │                 │             │                   │            │
└────────────┼─────────────────┼─────────────┼───────────────────┼────────────┘
             │                 │             │                   │
     ┌───────▼───────┐   ┌─────▼─────┐ ┌─────▼─────┐   ┌─────────▼─────────┐
     │  Claude Code  │   │   Slack   │ │  Notion   │   │  SQLite Database  │
     │     CLI       │   │    API    │ │    API    │   │      (Local)      │
     └───────────────┘   └───────────┘ └───────────┘   └───────────────────┘
```

### 2.2 컴포넌트 설명

| 컴포넌트 | 책임 | 확장 포인트 |
|---------|------|------------|
| **Scheduler Service** | OS 스케줄러 연동, 작업 시간 관리 | 다른 스케줄러로 교체 가능 |
| **Command Handler** | Slack 명령어 파싱 및 처리 | 새 명령어 쉽게 추가 |
| **Report Generator** | 주간/월간 통계 리포트 생성 | 리포트 형식 확장 가능 |
| **Error Handler** | 재시도 로직, 에러 알림 | 알림 채널 추가 가능 |
| **Core Engine** | 워크플로우 오케스트레이션 | 새 워크플로우 정의 가능 |
| **Content Generator** | 콘텐츠 생성 (Claude Code) | 다른 LLM으로 교체 가능 |
| **Slack Adapter** | Slack API 통신 | Discord 등으로 확장 |
| **Notion Adapter** | Notion API 통신 | Confluence 등으로 확장 |
| **Storage Layer** | 데이터 영속성 관리 | PostgreSQL 등으로 교체 |

---

## 3. 디렉토리 구조

```
daily-bot/
├── README.md
├── requirements.txt
├── setup.py
├── .env.example
├── .gitignore
├── config/
│   ├── __init__.py
│   ├── settings.py              # 환경 설정 로드
│   └── topics.py                # CS 주제 카테고리 정의
├── src/
│   ├── __init__.py
│   ├── main.py                  # 애플리케이션 진입점
│   ├── core/
│   │   ├── __init__.py
│   │   ├── engine.py            # 핵심 오케스트레이터
│   │   ├── scheduler.py         # 스케줄러 서비스
│   │   └── workflow.py          # 워크플로우 정의
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── models.py            # 도메인 모델 (Topic, Content, Report)
│   │   └── enums.py             # 열거형 (Category, Status)
│   ├── generators/
│   │   ├── __init__.py
│   │   ├── base.py              # ContentGenerator 인터페이스
│   │   ├── claude_code.py       # Claude Code CLI 구현체
│   │   └── prompts/
│   │       ├── __init__.py
│   │       └── cs_knowledge.py  # CS 지식 프롬프트 템플릿
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── slack/
│   │   │   ├── __init__.py
│   │   │   ├── adapter.py       # Slack API 어댑터
│   │   │   ├── commands.py      # 명령어 핸들러
│   │   │   └── formatters.py    # 메시지 포매터
│   │   └── notion/
│   │       ├── __init__.py
│   │       ├── adapter.py       # Notion API 어댑터
│   │       └── templates.py     # 페이지 템플릿
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── base.py              # Repository 인터페이스
│   │   ├── sqlite.py            # SQLite 구현체
│   │   └── migrations/
│   │       └── 001_initial.sql
│   ├── reports/
│   │   ├── __init__.py
│   │   ├── generator.py         # 리포트 생성기
│   │   └── templates.py         # 리포트 템플릿
│   ├── errors/
│   │   ├── __init__.py
│   │   ├── handler.py           # 에러 핸들러
│   │   └── retry.py             # 재시도 로직
│   └── utils/
│       ├── __init__.py
│       ├── logger.py            # 로깅 유틸리티
│       └── datetime_utils.py    # 날짜/시간 유틸리티
├── scripts/
│   ├── install_windows.ps1      # Windows 설치 스크립트
│   ├── install_macos.sh         # macOS 설치 스크립트
│   ├── setup_scheduler.py       # 스케줄러 등록
│   └── uninstall.py             # 제거 스크립트
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # pytest 설정
│   ├── unit/
│   │   ├── test_engine.py
│   │   ├── test_generators.py
│   │   ├── test_storage.py
│   │   └── test_reports.py
│   └── integration/
│       ├── test_slack.py
│       └── test_notion.py
└── docs/
    ├── INSTALLATION.md          # 설치 가이드
    ├── CONFIGURATION.md         # 설정 가이드
    └── COMMANDS.md              # Slack 명령어 가이드
```

---

## 4. 핵심 인터페이스 설계

### 4.1 Content Generator Interface

```python
from abc import ABC, abstractmethod
from typing import Optional
from domain.models import Content, Topic

class ContentGenerator(ABC):
    """콘텐츠 생성기 인터페이스 - 확장 포인트"""
    
    @abstractmethod
    async def generate(
        self, 
        topic: Optional[Topic] = None,
        category: Optional[str] = None
    ) -> Content:
        """
        콘텐츠 생성
        
        Args:
            topic: 특정 주제 (없으면 자동 선택)
            category: 카테고리 필터
            
        Returns:
            생성된 Content 객체
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """생성기 상태 확인"""
        pass
```

### 4.2 Messaging Adapter Interface

```python
from abc import ABC, abstractmethod
from typing import Optional
from domain.models import Content, Report

class MessagingAdapter(ABC):
    """메시징 어댑터 인터페이스 - Slack, Discord 등 확장 가능"""
    
    @abstractmethod
    async def send_content(
        self, 
        channel: str, 
        content: Content,
        notion_url: str
    ) -> bool:
        """콘텐츠 요약 메시지 전송"""
        pass
    
    @abstractmethod
    async def send_error(
        self, 
        user_id: str, 
        error_message: str
    ) -> bool:
        """에러 DM 전송"""
        pass
    
    @abstractmethod
    async def send_report_notification(
        self, 
        channel: str, 
        report: Report,
        notion_url: str
    ) -> bool:
        """리포트 알림 전송"""
        pass
```

### 4.3 Document Storage Interface

```python
from abc import ABC, abstractmethod
from typing import Optional
from domain.models import Content, PageInfo

class DocumentStorage(ABC):
    """문서 저장소 인터페이스 - Notion, Confluence 등 확장 가능"""
    
    @abstractmethod
    async def create_page(
        self, 
        content: Content
    ) -> PageInfo:
        """콘텐츠 페이지 생성"""
        pass
    
    @abstractmethod
    async def create_report_page(
        self, 
        report: Report
    ) -> PageInfo:
        """리포트 페이지 생성"""
        pass
```

### 4.4 Repository Interface

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime
from domain.models import Topic, ContentRecord

class ContentRepository(ABC):
    """데이터 저장소 인터페이스 - SQLite, PostgreSQL 등 확장 가능"""
    
    @abstractmethod
    async def save_content(self, record: ContentRecord) -> int:
        """콘텐츠 기록 저장"""
        pass
    
    @abstractmethod
    async def get_recent_topics(
        self, 
        days: int = 30
    ) -> List[str]:
        """최근 N일간 발송된 주제 목록"""
        pass
    
    @abstractmethod
    async def get_statistics(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> dict:
        """기간별 통계 조회"""
        pass
```

---

## 5. 데이터 모델

### 5.1 SQLite 스키마

```sql
-- 콘텐츠 발송 기록
CREATE TABLE content_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic VARCHAR(200) NOT NULL,
    category VARCHAR(50) NOT NULL,
    summary TEXT NOT NULL,
    notion_url VARCHAR(500),
    slack_ts VARCHAR(50),
    status VARCHAR(20) DEFAULT 'success',
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_name VARCHAR(100)
);

-- 스케줄 설정
CREATE TABLE schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    time VARCHAR(5) NOT NULL,          -- "07:00"
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 실행 로그
CREATE TABLE execution_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_id INTEGER,
    status VARCHAR(20) NOT NULL,
    error_message TEXT,
    duration_ms INTEGER,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (schedule_id) REFERENCES schedules(id)
);

-- 주제 요청 대기열
CREATE TABLE topic_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    requested_by VARCHAR(100) NOT NULL,
    topic VARCHAR(200) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
);

-- 인덱스
CREATE INDEX idx_content_created_at ON content_records(created_at);
CREATE INDEX idx_content_category ON content_records(category);
CREATE INDEX idx_logs_executed_at ON execution_logs(executed_at);
```

### 5.2 Notion 데이터베이스 속성

> **Note**: Notion API `2025-09-03` (`data_sources` 모델) 사용. 속성은 봇이 자동으로 생성/관리합니다.

| 속성명 | 타입 | 설명 |
|-------|------|------|
| 제목 | Title | 콘텐츠 제목 |
| 카테고리 | Select | Network, OS, Algorithm 등 12개 카테고리 |
| 태그 | Multi-select | 관련 키워드 태그 |
| 난이도 | Select | 초급, 중급, 고급 |
| 작성일 | Date | 생성 일시 |
| 작성자 | Rich Text | 발송한 팀원 이름 |
| 상태 | Select | 발행됨 |

페이지 본문은 callout 블록으로 요약 내용을 표시합니다.

---

## 6. 주요 기능 상세

### 6.1 Slack 명령어

| 명령어 | 설명 | 예시 |
|--------|------|------|
| `/daily-bot time <HH:MM>` | 스케줄 시간 변경 | `/daily-bot time 08:00` |
| `/daily-bot add <HH:MM>` | 스케줄 추가 | `/daily-bot add 18:00` |
| `/daily-bot pause` | 스케줄 일시 정지 | `/daily-bot pause` |
| `/daily-bot resume` | 스케줄 재개 | `/daily-bot resume` |
| `/daily-bot now` | 즉시 실행 | `/daily-bot now` |
| `/daily-bot request "<topic>"` | 특정 주제 요청 | `/daily-bot request "TCP 3-way handshake"` |
| `/daily-bot status` | 현재 상태 확인 | `/daily-bot status` |
| `/daily-bot help` | 도움말 | `/daily-bot help` |

### 6.2 재시도 로직

```python
RETRY_CONFIG = {
    "max_attempts": 5,
    "intervals_minutes": [5, 10, 15, 20, 25],  # 점진적 증가
    "on_failure": "skip_and_notify"
}
```

**재시도 플로우:**
1. 1차 실패 → 5분 후 재시도
2. 2차 실패 → 10분 후 재시도
3. 3차 실패 → 15분 후 재시도
4. 4차 실패 → 20분 후 재시도
5. 5차 실패 → 25분 후 재시도
6. 최종 실패 → Slack DM으로 에러 알림, 해당 날짜 스킵

### 6.3 로그 관리

```python
LOG_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file_path": "logs/daily-bot.log",
    "rotation": "daily",
    "retention_days": 90,  # 3개월
    "backup_count": 90
}
```

### 6.4 통계 리포트

**주간 리포트 (매주 월요일 10:00)**
- 발송 총 건수
- 카테고리별 분포 (차트)
- 실패/재시도 통계
- 아직 다루지 않은 주제 영역 추천

**월간 리포트 (매월 1일 10:00)**
- 월간 발송 총 건수
- 카테고리별 분포 추이
- 성공률 통계
- 주제 커버리지 분석
- 다음 달 추천 주제 영역

---

## 7. 크로스 플랫폼 지원

### 7.1 스케줄러 구현

| OS | 스케줄러 | 절전 모드 해제 |
|----|---------|---------------|
| Windows | Task Scheduler | "Wake the computer to run this task" 옵션 |
| macOS | launchd | `StartCalendarInterval` + pmset 설정 |

### 7.2 설치 방식

**Windows:**
```powershell
# PowerShell 스크립트 실행
.\scripts\install_windows.ps1
```

**macOS:**
```bash
# Shell 스크립트 실행
./scripts/install_macos.sh
```

---

## 8. 보안

### 8.1 현재 구현 (.env)

```env
# .env.example
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_CHANNEL_ID=C0XXXXXXX
SLACK_USER_ID=U0XXXXXXX

NOTION_API_KEY=secret_XXXXXXXX
NOTION_DATABASE_ID=XXXXXXXX

USER_NAME=your-name
```

### 8.2 향후 강화 옵션

1. **암호화된 설정 파일**: Fernet 대칭 암호화 적용
2. **OS 자격 증명 관리자**: keyring 라이브러리 활용
3. **환경 변수**: 시스템 환경 변수로 민감 정보 관리

---

## 9. 확장성 설계

### 9.1 새 콘텐츠 타입 추가 예시

```python
# generators/tech_news.py
class TechNewsGenerator(ContentGenerator):
    """기술 뉴스 생성기 - CS 지식 외 다른 콘텐츠"""
    
    async def generate(self, topic=None, category=None) -> Content:
        # 기술 뉴스 생성 로직
        pass
```

### 9.2 새 메시징 플랫폼 추가 예시

```python
# integrations/discord/adapter.py
class DiscordAdapter(MessagingAdapter):
    """Discord 메시징 어댑터"""
    
    async def send_content(self, channel, content, notion_url) -> bool:
        # Discord 전송 로직
        pass
```

### 9.3 설정을 통한 컴포넌트 교체

```python
# config/settings.py
COMPONENTS = {
    "content_generator": "generators.claude_code.ClaudeCodeGenerator",
    "messaging_adapter": "integrations.slack.adapter.SlackAdapter",
    "document_storage": "integrations.notion.adapter.NotionAdapter",
    "repository": "storage.sqlite.SQLiteRepository",
}
```

---

## 10. 개발 계획

### Phase 1: 핵심 기능 (1주)
- [ ] 프로젝트 구조 생성
- [ ] 도메인 모델 정의
- [ ] Claude Code 연동
- [ ] SQLite 저장소 구현
- [ ] 기본 워크플로우 구현

### Phase 2: 통합 (1주)
- [ ] Notion API 연동
- [ ] Slack 메시지 전송
- [ ] 스케줄러 구현 (Windows/macOS)
- [ ] 절전 모드 해제 기능

### Phase 3: 명령어 및 리포트 (1주)
- [ ] Slack 명령어 핸들러
- [ ] 재시도 로직
- [ ] 에러 알림
- [ ] 주간/월간 리포트 생성

### Phase 4: 품질 및 문서화 (3일)
- [ ] 단위 테스트 작성
- [ ] 통합 테스트 작성
- [ ] README 및 설치 가이드
- [ ] 코드 품질 도구 설정

---

## 11. 기술 스택 요약

| 구분 | 기술 |
|------|------|
| 언어 | Python 3.11+ |
| 패키지 관리 | pip + requirements.txt |
| 데이터베이스 | SQLite |
| Slack SDK | slack-sdk |
| Notion SDK | notion-client |
| 스케줄링 | APScheduler + OS 스케줄러 |
| 테스트 | pytest, pytest-asyncio |
| 코드 품질 | black, ruff, mypy |
| 로깅 | Python logging + RotatingFileHandler |

---

## 12. 의존성 (requirements.txt)

```
# Core
python-dotenv>=1.0.0
pydantic>=2.0.0
aiosqlite>=0.19.0

# Integrations
slack-sdk>=3.21.0
notion-client>=2.0.0

# Scheduling
apscheduler>=3.10.0

# Utilities
aiohttp>=3.9.0
tenacity>=8.2.0  # 재시도 로직

# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0

# Code Quality
black>=23.0.0
ruff>=0.1.0
mypy>=1.5.0
```

---

*문서 버전: 1.1*
*최종 수정: 2026-02-05*
