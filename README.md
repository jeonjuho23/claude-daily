# Daily-Bot 🤖

개발자를 위한 자동화된 CS 지식 공유 봇

매일 정해진 시간에 Claude Code를 활용하여 CS(Computer Science) 관련 학습 콘텐츠를 자동으로 생성하고, Slack에 게시합니다. Notion 연동은 선택 사항입니다.

## ✨ 주요 기능

- **자동 콘텐츠 생성**: Claude Code CLI를 활용한 고품질 CS 지식 콘텐츠 생성
- **다중 플랫폼 지원**: Windows와 macOS 모두 지원
- **Slack 연동**: 요약 내용 및 링크 자동 게시, 슬래시 명령어 지원
- **Notion 연동 (Optional)**: 요약 콘텐츠 페이지 자동 생성 (callout 블록)
- **스케줄 관리**: 다중 스케줄 설정, 일시정지/재개
- **절전 모드 해제**: Windows Task Scheduler / macOS launchd를 통한 자동 실행
- **재시도 로직**: 실패 시 점진적 재시도 (5회, 5분 단위 증가)
- **주간/월간 리포트**: 자동 통계 리포트 생성

## 📁 프로젝트 구조

```
daily-bot/
├── config/                 # 설정 파일
│   ├── settings.py         # 환경 설정 관리
│   └── topics.py           # CS 주제 정의
├── src/
│   ├── core/               # 핵심 엔진
│   │   └── engine.py       # 메인 오케스트레이터
│   ├── domain/             # 도메인 모델
│   │   ├── enums.py        # 열거형 정의
│   │   └── models.py       # 데이터 모델
│   ├── generators/         # 콘텐츠 생성기
│   │   ├── base.py         # 추상 인터페이스
│   │   ├── claude_code_generator.py
│   │   └── prompts/        # 프롬프트 템플릿
│   ├── integrations/       # 외부 연동
│   │   ├── slack/          # Slack 어댑터
│   │   └── notion/         # Notion 어댑터
│   ├── storage/            # 데이터 저장소
│   │   ├── base.py         # 추상 인터페이스
│   │   └── sqlite_repository.py
│   ├── reports/            # 리포트 생성
│   ├── errors/             # 에러 핸들링
│   └── utils/              # 유틸리티
├── scripts/                # 플랫폼별 스크립트
├── tests/                  # 테스트
├── main.py                 # 엔트리 포인트
├── requirements.txt        # 의존성
├── .env.example            # 환경변수 템플릿
└── CHANGELOG.md            # 변경 로그
```

## 🚀 설치 및 실행

### 사전 요구사항

- Python 3.11 이상
- Node.js (Claude Code CLI 설치용)
- Slack 워크스페이스 관리 권한
- Notion Integration 생성 권한 (Optional)

### 1. 클론 및 의존성 설치

```bash
git clone https://github.com/jeonjuho23/claude-daily.git
cd claude-daily
pip install -r requirements.txt
```

Claude Code CLI 설치 (아직 없다면):

```bash
npm install -g @anthropic-ai/claude-code
claude --version   # 설치 확인
```

### 2. Slack 앱 설정

[Slack API](https://api.slack.com/apps)에서 새 앱을 생성합니다.

1. **Create New App** > From scratch > 앱 이름, 워크스페이스 선택
2. **Settings > Socket Mode** > 활성화 > Token 생성 (`xapp-` 으로 시작)
3. **Features > OAuth & Permissions** > Bot Token Scopes 추가:
   - `chat:write` - 메시지 전송
   - `commands` - 슬래시 명령어
   - `app_mentions:read` - 멘션 읽기
4. **Install App to Workspace** > Bot User OAuth Token 복사 (`xoxb-`)
5. **Features > Slash Commands** > `/daily-bot` 추가 (Request URL은 Socket Mode라 불필요)
6. **Settings > Basic Information** > Signing Secret 복사
7. 발행할 Slack 채널에서 봇 초대: `/invite @앱이름`
8. 채널 ID 확인: 채널명 우클릭 > 채널 세부정보 > 하단의 채널 ID

### 3. Notion 설정 (Optional)

Notion 설정 없이도 Slack만으로 봇이 정상 동작합니다. Notion에 콘텐츠/리포트를 기록하려면:

[Notion Integrations](https://www.notion.so/my-integrations)에서 Integration을 생성합니다.

1. **New integration** > Internal integration > 생성 후 API Key 복사 (`secret_` 으로 시작)
2. Notion에서 빈 데이터베이스 생성 (속성은 봇이 자동으로 추가합니다)
   - 자동 생성 속성: 제목, 카테고리, 난이도, 태그, 작성일, 작성자, 상태
3. 데이터베이스 페이지에서 `...` > **연결** > 생성한 Integration 추가
4. 데이터베이스 URL에서 ID 추출: `notion.so/{DATABASE_ID}?v=...`

### 4. 환경변수 설정

```bash
cp .env.example .env
```

`.env` 파일을 열어 2-3단계에서 복사한 값을 입력합니다:

```env
# Slack (필수)
SLACK_BOT_TOKEN=xoxb-실제토큰
SLACK_SIGNING_SECRET=실제시크릿
SLACK_APP_TOKEN=xapp-실제토큰
SLACK_CHANNEL_ID=C실제채널ID

# 봇 설정
BOT_OWNER_NAME=본인이름
DEFAULT_SCHEDULE_TIME=07:00
TIMEZONE=Asia/Seoul

# Notion (Optional - 설정 시 Notion 연동 활성화)
# NOTION_API_KEY=secret_실제키
# NOTION_DATABASE_ID=실제데이터베이스ID
```

전체 설정 항목은 `.env.example` 참조.

### 5. 실행

```bash
python main.py
```

시작 시 health check 결과가 표시됩니다:

```
Slack API: OK
Notion API: OK (또는 SKIPPED (not configured))
Claude Code CLI: OK
Daily-Bot is running. Press Ctrl+C to stop.
```

Slack/Claude OK면 정상. Notion 미설정 시 SKIPPED 표시되며 Slack만으로 동작합니다. `DEFAULT_SCHEDULE_TIME`에 자동으로 콘텐츠 생성/발행됩니다.

> **중요**: `python main.py`는 한번 실행하고 끝나는 스크립트가 아닙니다.
> APScheduler가 내장된 **상시 실행 프로세스(데몬)** 로, 프로세스가 살아있는 동안 설정 시간에 자동 실행됩니다.
> Ctrl+C로 종료합니다.

### 6. 백그라운드 실행 (터미널 꺼도 유지)

#### Windows (PowerShell)

```powershell
Start-Process python -ArgumentList "main.py" -WorkingDirectory "C:\path\to\claude-daily" -WindowStyle Hidden
```

#### Linux (systemd)

```bash
sudo cp scripts/daily-bot.service /etc/systemd/system/
# /etc/systemd/system/daily-bot.service 내 경로/사용자 수정
sudo systemctl enable daily-bot
sudo systemctl start daily-bot
```

### 7. 동작 확인

- **로그**: `logs/` 디렉토리에 자동 생성
- **상태 확인**: Slack에서 `/daily-bot status`
- **즉시 테스트**: Slack에서 `/daily-bot now`

## 📖 사용 방법

### Slack 명령어

| 명령어 | 설명 |
|--------|------|
| `/daily-bot help` | 도움말 표시 |
| `/daily-bot status` | 현재 상태 확인 |
| `/daily-bot time <HH:MM>` | 기본 스케줄 시간 변경 |
| `/daily-bot add <HH:MM>` | 스케줄 추가 |
| `/daily-bot remove <HH:MM>` | 스케줄 삭제 |
| `/daily-bot list` | 스케줄 목록 |
| `/daily-bot pause` | 일시정지 |
| `/daily-bot resume` | 재개 |
| `/daily-bot now` | 즉시 실행 |
| `/daily-bot request "<주제>"` | 특정 주제 요청 |

## 📊 CS 주제 카테고리

- 네트워크 (Network)
- 운영체제 (OS)
- 알고리즘 (Algorithm)
- 자료구조 (Data Structure)
- 데이터베이스 (Database)
- 객체지향 프로그래밍 (OOP)
- 도메인 주도 설계 (DDD)
- 테스트 주도 개발 (TDD)
- 디자인 패턴 (Design Pattern)
- 소프트웨어 아키텍처 (Architecture)
- 보안 (Security)
- DevOps

## 🔧 확장성

인터페이스 기반 설계로 각 컴포넌트를 쉽게 교체할 수 있습니다:

```python
# 예: Claude API로 콘텐츠 생성기 교체
from src.generators import ContentGenerator

class ClaudeAPIGenerator(ContentGenerator):
    async def generate(self, topic, category, difficulty, language):
        # Anthropic API 직접 호출 구현
        pass
```

## 🔄 재시도 로직

실패 시 점진적 재시도:
1. 5분 후 재시도
2. 10분 후 재시도
3. 15분 후 재시도
4. 20분 후 재시도
5. 25분 후 최종 재시도

5회 모두 실패 시 Slack DM으로 오류 알림

## 📝 라이선스

MIT License

## 🤝 기여

이슈 및 PR 환영합니다!
