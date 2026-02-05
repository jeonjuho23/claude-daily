"""
Prompt templates for content generation
"""

# Korean language prompt template
CONTENT_GENERATION_PROMPT_KO = """당신은 CS(Computer Science) 지식을 개발자들에게 쉽고 명확하게 설명하는 기술 콘텐츠 작성자입니다.

## 작성 요청
다음 주제에 대해 개발자를 위한 요약 콘텐츠를 작성해주세요:

**주제:** {topic}
**카테고리:** {category}
**난이도:** {difficulty}

## 출력 형식
반드시 아래 JSON 형식으로만 출력하세요. JSON 외의 다른 텍스트는 절대 포함하지 마세요.

```json
{{
    "title": "주제 제목",
    "summary": "핵심 요약 (3-5문장, 300자 이내)",
    "tags": ["태그1", "태그2", "태그3"]
}}
```

## 작성 가이드라인

### Summary (요약)
- Slack과 Notion에 게시될 핵심 내용
- 3-5문장으로 주제의 핵심 개념과 왜 중요한지 전달
- 실무 개발자가 바로 이해할 수 있는 수준
- 300자 이내

### Tags
- 3-5개의 관련 태그
- 카테고리 관련 태그 1개 이상 포함

### 난이도별 작성 수준
- 초급: 기본 개념 위주, 쉬운 용어
- 중급: 실무 적용 중심, 적절한 기술 용어
- 고급: 심화 내용, 트레이드오프 포함
"""

# English language prompt template
CONTENT_GENERATION_PROMPT_EN = """You are a technical content writer who explains CS (Computer Science) knowledge to developers in a clear and accessible way.

## Request
Please write a summary for developers on the following topic:

**Topic:** {topic}
**Category:** {category}
**Difficulty:** {difficulty}

## Output Format
You must output JSON in exactly this format. Do not include any other text outside the JSON.

```json
{{
    "title": "Topic Title",
    "summary": "Core summary (3-5 sentences, under 300 characters)",
    "tags": ["tag1", "tag2", "tag3"]
}}
```

## Guidelines

### Summary
- Core content to be posted on Slack and Notion
- 3-5 sentences covering the key concept and why it matters
- Practical level that working developers can immediately understand
- Under 300 characters

### Tags
- 3-5 related tags
- Include at least one category-related tag

### Difficulty levels
- Beginner: Focus on basics, use simple terms
- Intermediate: Focus on practical application, appropriate technical terms
- Advanced: Deep dive, trade-offs included
"""


def get_generation_prompt(
    topic: str,
    category: str,
    difficulty: str,
    language: str = "ko",
) -> str:
    """
    Get the appropriate prompt template with values filled in
    
    Args:
        topic: Topic to generate content for
        category: Content category
        difficulty: Difficulty level
        language: Language (ko or en)
        
    Returns:
        Formatted prompt string
    """
    template = CONTENT_GENERATION_PROMPT_KO if language == "ko" else CONTENT_GENERATION_PROMPT_EN
    
    return template.format(
        topic=topic,
        category=category,
        difficulty=difficulty,
    )
