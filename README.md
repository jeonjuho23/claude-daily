# Daily-Bot 🤖

개발자를 위한 자동화된 CS 지식 공유 봇

매일 정해진 시간에 Claude Code를 활용하여 CS(Computer Science) 관련 학습 콘텐츠를 자동으로 생성하고, Slack과 Notion에 게시합니다.

## ✨ 주요 기능

- **자동 콘텐츠 생성**: Claude Code CLI를 활용한 고품질 CS 지식 콘텐츠 생성
- **다중 플랫폼 지원**: Windows와 macOS 모두 지원
- **Slack 연동**: 요약 내용 및 링크 자동 게시, 슬래시 명령어 지원
- **Notion 연동**: 요약 콘텐츠 페이지 자동 생성 (callout 블록)
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

## 🚀 설치 방법

### 사전 요구사항

- Python 3.11 이상
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) 설치 및 인증
- Slack 워크스페이스 관리 권한
- Notion Integration 생성 권한

### 1. 저장소 클론

```bash
git clone https://github.com/your-repo/daily-bot.git
cd daily-bot
```

### 2. 환경 설정

#### Windows

```batch
scripts\setup_windows.bat
```

#### macOS

```bash
chmod +x scripts/*.sh
./scripts/setup_macos.sh
```

### 3. 환경변수 설정

`.env.example`을 `.env`로 복사하고 설정을 입력합니다:

```bash
cp .env.example .env
```

#### 필수 설정 항목

```env
# Slack 설정
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_APP_TOKEN=xapp-your-app-token
SLACK_CHANNEL_ID=C01234567

# Notion 설정
NOTION_API_KEY=secret_your-api-key
NOTION_DATABASE_ID=your-database-id
```

### 4. Slack 앱 설정

1. [Slack API](https://api.slack.com/apps)에서 앱 생성
2. **Socket Mode** 활성화
3. **Event Subscriptions** 활성화
4. 필요한 **OAuth Scopes** 추가:
   - `chat:write`
   - `commands`
   - `im:write`
5. **Slash Commands** 추가: `/daily-bot`

### 5. Notion 설정

1. [Notion Integrations](https://www.notion.so/my-integrations)에서 Integration 생성
2. 빈 데이터베이스 생성 (속성은 봇이 자동으로 추가합니다)
   - 자동 생성되는 속성: 제목, 카테고리, 난이도, 태그, 작성일, 작성자, 상태
3. 데이터베이스에 Integration 연결
4. 데이터베이스 URL에서 ID 추출 (예: `notion.so/` 뒤의 32자리 hex)

### 6. 스케줄 등록

#### Windows (Task Scheduler)

```batch
scripts\install_task.bat
```

#### macOS (launchd)

```bash
./scripts/install_launchd.sh
```

## 📖 사용 방법

### 수동 실행

```bash
# 가상환경 활성화
source venv/bin/activate  # macOS/Linux
# 또는
venv\Scripts\activate     # Windows

# 실행
python main.py
```

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
