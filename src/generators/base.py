"""
Abstract base interface for content generators
Allows swapping generation implementations (Claude Code CLI → API, etc.)
"""

from abc import ABC, abstractmethod

from src.domain.enums import Category, Difficulty
from src.domain.models import GeneratedContent


class ContentGenerator(ABC):
    """Abstract base class for content generation"""

    @abstractmethod
    async def generate(
        self,
        topic: str,
        category: Category,
        difficulty: Difficulty = Difficulty.INTERMEDIATE,
        language: str = "ko",
    ) -> GeneratedContent:
        """
        Generate content for a given topic

        Args:
            topic: The topic to generate content for
            category: Content category
            difficulty: Content difficulty level
            language: Language for content (ko, en)

        Returns:
            Generated content

        Raises:
            GenerationError: If generation fails
        """
        pass

    @abstractmethod
    async def generate_random(
        self,
        used_topics: list[str] | None = None,
        preferred_category: Category | None = None,
        language: str = "ko",
    ) -> GeneratedContent:
        """
        Generate content for a random topic

        Args:
            used_topics: List of already used topic titles to avoid
            preferred_category: Preferred category (optional)
            language: Language for content

        Returns:
            Generated content

        Raises:
            GenerationError: If generation fails
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the generator is available and working

        Returns:
            True if healthy, False otherwise
        """
        pass


class GenerationError(Exception):
    """Exception raised when content generation fails"""

    def __init__(self, message: str, original_error: Exception | None = None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)
