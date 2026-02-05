"""
Prompt templates for content generation
"""

from src.generators.prompts.templates import (
    CONTENT_GENERATION_PROMPT_KO,
    CONTENT_GENERATION_PROMPT_EN,
    get_generation_prompt,
)

__all__ = [
    "CONTENT_GENERATION_PROMPT_KO",
    "CONTENT_GENERATION_PROMPT_EN",
    "get_generation_prompt",
]
