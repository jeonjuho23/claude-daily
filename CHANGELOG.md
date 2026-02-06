# Changelog

## [0.3.0] - 2026-02-06

### Notion 통합 Optional화
- `NOTION_API_KEY`, `NOTION_DATABASE_ID`를 Optional 필드로 변경
- `settings.notion_enabled` 프로퍼티 추가 (두 값 모두 설정 시 True)
- Notion 미설정 시 Slack만으로 봇이 정상 동작
- `CoreEngine`, `ReportGenerator`에서 `notion_adapter` 파라미터 Optional화
- Health check: Notion 미설정 시 `SKIPPED (not configured)` 표시

### 테스트 개선
- Settings 테스트에서 `.env.example` 사용하여 실제 `.env` 의존성 제거
- `notion_enabled` 프로퍼티 테스트 5개 추가 (True, None, 빈 문자열, 양방향 partial)
- Notion 없이 콘텐츠 발행 테스트 3개 추가 (engine)
- Notion 없이 리포트 생성 테스트 3개 추가 (report_generator)
- 총 288개 테스트 (전체 통과)

### 문서
- README.md, CLAUDE.md, daily-bot-architecture.md: Notion Optional 반영
- `.env.example`: Notion 섹션 주석 처리

## [0.2.0] - 2026-02-05

### Notion API 마이그레이션
- `notion-client` 2.7.0 (API `2025-09-03`)의 `data_sources` 모델로 전환
- `_get_data_source_id()`: 데이터베이스에서 data_source_id 자동 추출
- `_ensure_database_schema()`: `data_sources.update`로 속성 자동 관리
- 페이지 생성: `parent.database_id` -> `parent.data_source_id`
- 타이틀 속성 "이름" -> "제목" 자동 이름 변경 로직

### 콘텐츠 생성 간소화
- 상세 본문(content) 생성 제거, 요약(summary)만 생성
- 프롬프트: title + summary + tags만 요청 (JSON 잘림 문제 해결)
- 생성 시간 42초 -> 10초로 단축
- 잘린 JSON 복구 로직(`_recover_truncated_json`) 제거

### Notion 페이지 개선
- "요약" 속성 삭제
- 페이지 본문에 callout 블록으로 요약 표시
- 리포트도 동일 데이터베이스에 생성 (별도 리포트 페이지 불필요)

### Pydantic V2 마이그레이션
- 모든 모델의 `class Config` -> `model_config = ConfigDict(...)` 변경
- 대상: ContentRecord, Schedule, ExecutionLog, TopicRequest, ReportData, GeneratedContent

### execution_logs 성능 측정
- `duration_ms INTEGER` 컬럼 추가
- `time.perf_counter()`로 고해상도 실행 시간 측정
- 리포트에 평균/최소/최대 실행 시간 통계 추가

### 버그 수정
- Windows SIGTERM 호환성 (win32에서 SIGTERM 등록 스킵)
- Settings Lazy Loading (`_LazySettings` 프록시로 지연 로딩)
- SQLite 동시 접근 Lock (`asyncio.Lock` 적용)
- Async Task 예외 처리 (`create_background_task` 콜백)
- Claude CLI stdin 방식 (`-p -`으로 프롬프트 전달)
- Windows cp949 인코딩 오류 (Unicode 문자 -> ASCII 대체)

### 테스트 확대
- 76개 테스트 (18개 -> 76개)
- 신규: test_topics.py, test_settings.py, test_async_utils.py, test_repository.py

### 문서
- .env.example 추가
- CHANGELOG.md 추가
- README.md, CLAUDE.md, daily-bot-architecture.md 업데이트

## [0.1.0] - 2026-02-05

### 초기 구현
- 프로젝트 구조 생성
- 도메인 모델 정의 (Pydantic)
- Claude Code CLI 연동 콘텐츠 생성기
- Slack 어댑터 (Socket Mode, 슬래시 명령어)
- Notion 어댑터 (페이지 생성)
- SQLite 저장소 (aiosqlite)
- APScheduler 기반 스케줄링
- 재시도 로직 (5회, 점진적 간격)
- 주간/월간 리포트 생성
- 240+ CS 주제 (12개 카테고리)
