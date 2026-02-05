"""
CS Topics Definition for Daily-Bot
Contains all available topics organized by category
"""

# Category definitions with Korean and English names
CATEGORIES: dict[str, dict[str, str]] = {
    "network": {"ko": "네트워크", "en": "Network"},
    "os": {"ko": "운영체제", "en": "Operating System"},
    "algorithm": {"ko": "알고리즘", "en": "Algorithm"},
    "data_structure": {"ko": "자료구조", "en": "Data Structure"},
    "database": {"ko": "데이터베이스", "en": "Database"},
    "oop": {"ko": "객체지향프로그래밍", "en": "OOP"},
    "ddd": {"ko": "도메인 주도 설계", "en": "Domain-Driven Design"},
    "tdd": {"ko": "테스트 주도 개발", "en": "Test-Driven Development"},
    "design_pattern": {"ko": "디자인 패턴", "en": "Design Pattern"},
    "architecture": {"ko": "소프트웨어 아키텍처", "en": "Software Architecture"},
    "security": {"ko": "보안", "en": "Security"},
    "devops": {"ko": "DevOps", "en": "DevOps"},
}

# Topics by category
TOPICS: dict[str, list[str]] = {
    "network": [
        "OSI 7계층과 TCP/IP 4계층",
        "TCP vs UDP 비교",
        "TCP 3-way handshake와 4-way handshake",
        "HTTP/1.1 vs HTTP/2 vs HTTP/3",
        "HTTPS와 TLS 동작 원리",
        "DNS 동작 원리와 레코드 타입",
        "로드밸런싱 알고리즘",
        "CDN (Content Delivery Network)",
        "웹소켓 (WebSocket) 프로토콜",
        "REST API vs GraphQL",
        "gRPC 프로토콜",
        "CORS (Cross-Origin Resource Sharing)",
        "NAT와 포트 포워딩",
        "VPN 동작 원리",
        "SDN (Software Defined Networking)",
        "서브넷 마스크와 CIDR",
        "ARP 프로토콜",
        "DHCP 동작 원리",
        "BGP 라우팅 프로토콜",
        "QUIC 프로토콜",
    ],
    "os": [
        "프로세스와 스레드의 차이",
        "컨텍스트 스위칭",
        "CPU 스케줄링 알고리즘",
        "데드락 (Deadlock) 조건과 해결",
        "메모리 관리 - 페이징과 세그멘테이션",
        "가상 메모리와 페이지 교체 알고리즘",
        "파일 시스템 구조",
        "프로세스 동기화 - 뮤텍스, 세마포어",
        "인터럽트와 시스템 콜",
        "IPC (Inter-Process Communication)",
        "캐시 메모리와 지역성",
        "동시성 vs 병렬성",
        "Race Condition과 해결 방법",
        "커널 모드와 사용자 모드",
        "부팅 프로세스",
        "메모리 단편화",
        "스와핑 (Swapping)",
        "Copy-on-Write",
        "시스템 콜 vs 라이브러리 함수",
        "실시간 운영체제 (RTOS)",
    ],
    "algorithm": [
        "시간복잡도와 공간복잡도",
        "정렬 알고리즘 비교 (퀵, 머지, 힙)",
        "이진 탐색 (Binary Search)",
        "동적 프로그래밍 (Dynamic Programming)",
        "그리디 알고리즘",
        "분할 정복 (Divide and Conquer)",
        "BFS와 DFS",
        "다익스트라 알고리즘",
        "벨만-포드 알고리즘",
        "플로이드-워셜 알고리즘",
        "최소 신장 트리 (Kruskal, Prim)",
        "위상 정렬",
        "유니온 파인드 (Union-Find)",
        "KMP 문자열 매칭",
        "라빈-카프 알고리즘",
        "슬라이딩 윈도우",
        "투 포인터",
        "백트래킹",
        "비트마스킹",
        "세그먼트 트리",
    ],
    "data_structure": [
        "배열 vs 연결 리스트",
        "스택과 큐",
        "해시 테이블과 충돌 해결",
        "이진 탐색 트리 (BST)",
        "균형 이진 트리 (AVL, Red-Black)",
        "힙 (Heap) 자료구조",
        "트라이 (Trie) 자료구조",
        "그래프 표현 방법",
        "B-Tree와 B+Tree",
        "LRU 캐시 구현",
        "블룸 필터 (Bloom Filter)",
        "스킵 리스트",
        "덱 (Deque)",
        "우선순위 큐",
        "그래프 - 인접 행렬 vs 인접 리스트",
        "이중 연결 리스트",
        "원형 큐",
        "해시맵 vs 해시셋",
        "트리 순회 방법",
        "이진 인덱스 트리 (Fenwick Tree)",
    ],
    "database": [
        "RDBMS vs NoSQL",
        "정규화와 역정규화",
        "인덱스 동작 원리",
        "트랜잭션 ACID 속성",
        "트랜잭션 격리 수준",
        "데드락 탐지와 해결",
        "SQL 조인 종류",
        "파티셔닝과 샤딩",
        "복제 (Replication) 전략",
        "CAP 이론",
        "MVCC (Multi-Version Concurrency Control)",
        "쿼리 최적화와 실행 계획",
        "커넥션 풀링",
        "Redis 자료구조와 활용",
        "데이터베이스 락 종류",
        "클러스터링 인덱스 vs 논클러스터링",
        "Write-Ahead Logging (WAL)",
        "이벤트 소싱",
        "CQRS 패턴",
        "데이터베이스 마이그레이션",
    ],
    "oop": [
        "캡슐화, 상속, 다형성, 추상화",
        "SOLID 원칙",
        "단일 책임 원칙 (SRP)",
        "개방-폐쇄 원칙 (OCP)",
        "리스코프 치환 원칙 (LSP)",
        "인터페이스 분리 원칙 (ISP)",
        "의존성 역전 원칙 (DIP)",
        "의존성 주입 (DI)",
        "추상 클래스 vs 인터페이스",
        "컴포지션 vs 상속",
        "오버로딩 vs 오버라이딩",
        "정적 바인딩 vs 동적 바인딩",
        "불변 객체 (Immutable Object)",
        "객체 동등성 vs 동일성",
        "DTO, VO, Entity 차이",
        "팩토리 메서드",
        "결합도와 응집도",
        "Law of Demeter",
        "Tell, Don't Ask 원칙",
        "GRASP 패턴",
    ],
    "ddd": [
        "도메인 주도 설계 개요",
        "유비쿼터스 언어 (Ubiquitous Language)",
        "바운디드 컨텍스트 (Bounded Context)",
        "컨텍스트 맵 (Context Map)",
        "엔티티 vs 값 객체",
        "애그리게이트 (Aggregate)",
        "도메인 이벤트",
        "리포지토리 패턴",
        "도메인 서비스",
        "애플리케이션 서비스",
        "안티코럽션 레이어",
        "공유 커널 (Shared Kernel)",
        "전략적 설계 vs 전술적 설계",
        "이벤트 스토밍",
        "도메인 모델링",
        "팩토리 패턴 in DDD",
        "스펙 (Specification) 패턴",
        "사이드 이펙트 없는 함수",
        "모듈 경계 정의",
        "마이크로서비스와 DDD",
    ],
    "tdd": [
        "TDD 개요와 레드-그린-리팩터",
        "단위 테스트 작성 원칙",
        "테스트 더블 (Mock, Stub, Spy)",
        "Given-When-Then 패턴",
        "테스트 커버리지",
        "테스트 피라미드",
        "통합 테스트 전략",
        "E2E 테스트",
        "BDD (Behavior-Driven Development)",
        "테스트 가능한 코드 설계",
        "의존성과 테스트 용이성",
        "테스트 격리",
        "Fixture와 Setup",
        "파라미터화 테스트",
        "Property-Based Testing",
        "뮤테이션 테스팅",
        "테스트 안티패턴",
        "TDD와 리팩토링",
        "레거시 코드 테스트",
        "테스트 주도 설계",
    ],
    "design_pattern": [
        "싱글톤 패턴",
        "팩토리 메서드 패턴",
        "추상 팩토리 패턴",
        "빌더 패턴",
        "프로토타입 패턴",
        "어댑터 패턴",
        "브릿지 패턴",
        "컴포지트 패턴",
        "데코레이터 패턴",
        "퍼사드 패턴",
        "플라이웨이트 패턴",
        "프록시 패턴",
        "책임 연쇄 패턴",
        "커맨드 패턴",
        "인터프리터 패턴",
        "이터레이터 패턴",
        "미디에이터 패턴",
        "메멘토 패턴",
        "옵저버 패턴",
        "전략 패턴",
        "템플릿 메서드 패턴",
        "비지터 패턴",
        "상태 패턴",
    ],
    "architecture": [
        "모놀리식 vs 마이크로서비스",
        "레이어드 아키텍처",
        "헥사고날 아키텍처",
        "클린 아키텍처",
        "이벤트 기반 아키텍처",
        "CQRS 패턴",
        "이벤트 소싱",
        "서비스 메시",
        "API 게이트웨이",
        "사이드카 패턴",
        "서킷 브레이커 패턴",
        "Saga 패턴",
        "스트랭글러 패턴",
        "벌크헤드 패턴",
        "12 Factor App",
        "서버리스 아키텍처",
        "멀티 테넌시",
        "캐싱 전략",
        "메시지 큐 아키텍처",
        "비동기 통신 패턴",
    ],
    "security": [
        "인증 vs 인가",
        "OAuth 2.0",
        "JWT (JSON Web Token)",
        "세션 기반 인증 vs 토큰 기반",
        "CORS와 보안",
        "XSS 공격과 방어",
        "CSRF 공격과 방어",
        "SQL 인젝션 방어",
        "암호화 - 대칭키 vs 비대칭키",
        "해시 함수와 솔팅",
        "HTTPS와 인증서",
        "Zero Trust 보안 모델",
        "OWASP Top 10",
        "보안 헤더 (CSP, HSTS)",
        "API 보안 베스트 프랙티스",
        "시크릿 관리",
        "2FA / MFA",
        "SSO (Single Sign-On)",
        "접근 제어 모델 (RBAC, ABAC)",
        "보안 감사 로깅",
    ],
    "devops": [
        "CI/CD 파이프라인",
        "Docker 컨테이너",
        "Kubernetes 기초",
        "Infrastructure as Code",
        "GitOps",
        "모니터링과 로깅 전략",
        "Prometheus와 Grafana",
        "ELK 스택",
        "Blue-Green 배포",
        "Canary 배포",
        "롤링 업데이트",
        "Feature Flag",
        "A/B 테스팅",
        "장애 대응 프로세스",
        "SRE (Site Reliability Engineering)",
        "SLI, SLO, SLA",
        "Chaos Engineering",
        "비용 최적화",
        "클라우드 네이티브 아키텍처",
        "Terraform과 Ansible",
    ],
}


def get_all_topics() -> list[tuple[str, str]]:
    """Get all topics with their categories"""
    result = []
    for category, topics in TOPICS.items():
        for topic in topics:
            result.append((category, topic))
    return result


def get_topics_by_category(category: str) -> list[str]:
    """Get topics for a specific category"""
    return TOPICS.get(category, [])


def get_category_name(category: str, lang: str = "ko") -> str:
    """Get category display name"""
    return CATEGORIES.get(category, {}).get(lang, category)


def get_total_topic_count() -> int:
    """Get total number of topics"""
    return sum(len(topics) for topics in TOPICS.values())


def infer_category_from_topic(topic: str) -> str | None:
    """
    Infer category from topic by matching against known topics

    Args:
        topic: The topic string to match

    Returns:
        Category string if found, None otherwise
    """
    topic_lower = topic.lower().strip()

    # Exact match first
    for category, topics in TOPICS.items():
        for known_topic in topics:
            if known_topic.lower() == topic_lower:
                return category

    # Partial match fallback
    for category, topics in TOPICS.items():
        for known_topic in topics:
            if topic_lower in known_topic.lower() or known_topic.lower() in topic_lower:
                return category

    return None
