"""
Claude Code CLI based content generator implementation
"""

import asyncio
import json
import random
import re
from typing import List, Optional

from src.generators.base import ContentGenerator, GenerationError
from src.generators.prompts import get_generation_prompt
from src.domain.models import GeneratedContent
from src.domain.enums import Category, Difficulty
from src.utils.logger import get_logger
from config.topics import TOPICS, CATEGORIES, get_category_name

logger = get_logger(__name__)


class ClaudeCodeGenerator(ContentGenerator):
    """
    Content generator using Claude Code CLI
    
    Executes claude code CLI commands to generate content.
    Requires Claude Code CLI to be installed and authenticated.
    """
    
    def __init__(
        self,
        timeout: int = 120,
        model: str = "claude-sonnet-4-20250514",
    ):
        """
        Initialize Claude Code generator
        
        Args:
            timeout: Command execution timeout in seconds
            model: Claude model to use
        """
        self.timeout = max(timeout, 180)
        self.model = model
    
    async def generate(
        self,
        topic: str,
        category: Category,
        difficulty: Difficulty = Difficulty.INTERMEDIATE,
        language: str = "ko",
    ) -> GeneratedContent:
        """
        Generate content for a given topic using Claude Code CLI
        """
        logger.info(
            "Generating content",
            topic=topic,
            category=category.value,
            difficulty=difficulty.value,
        )
        
        # Get category display name
        category_name = get_category_name(
            category.value if isinstance(category, Category) else category,
            language
        )
        
        # Get difficulty display name
        difficulty_name = difficulty.korean if language == "ko" else difficulty.value
        
        # Build prompt
        prompt = get_generation_prompt(
            topic=topic,
            category=category_name,
            difficulty=difficulty_name,
            language=language,
        )
        
        try:
            # Execute Claude Code CLI
            result = await self._execute_claude_code(prompt)
            
            # Parse the response
            content = self._parse_response(result, topic, category, difficulty)
            
            logger.info(
                "Content generated successfully",
                title=content.title,
            )
            
            return content
            
        except Exception as e:
            logger.error(
                "Content generation failed",
                topic=topic,
                error=str(e),
            )
            raise GenerationError(f"Failed to generate content: {e}", e)
    
    async def generate_random(
        self,
        used_topics: Optional[List[str]] = None,
        preferred_category: Optional[Category] = None,
        language: str = "ko",
    ) -> GeneratedContent:
        """
        Generate content for a random unused topic
        """
        used_topics = used_topics or []
        
        # Select category
        if preferred_category:
            category = preferred_category
        else:
            # Random category, weighted by remaining topics
            available_categories = []
            for cat, topics in TOPICS.items():
                available = [t for t in topics if t not in used_topics]
                if available:
                    available_categories.extend([cat] * len(available))
            
            if not available_categories:
                raise GenerationError("All topics have been used")
            
            category_str = random.choice(available_categories)
            category = Category(category_str)
        
        # Select topic from category
        category_str = category.value if isinstance(category, Category) else category
        available_topics = [
            t for t in TOPICS.get(category_str, [])
            if t not in used_topics
        ]
        
        if not available_topics:
            # Try other categories
            for cat, topics in TOPICS.items():
                available = [t for t in topics if t not in used_topics]
                if available:
                    category = Category(cat)
                    available_topics = available
                    break
        
        if not available_topics:
            raise GenerationError("No available topics")
        
        topic = random.choice(available_topics)
        
        # Random difficulty with weights (more intermediate)
        difficulties = [Difficulty.BEGINNER, Difficulty.INTERMEDIATE, Difficulty.ADVANCED]
        weights = [0.25, 0.5, 0.25]
        difficulty = random.choices(difficulties, weights=weights)[0]
        
        logger.info(
            "Selected random topic",
            topic=topic,
            category=category.value,
            difficulty=difficulty.value,
        )
        
        return await self.generate(
            topic=topic,
            category=category,
            difficulty=difficulty,
            language=language,
        )
    
    async def health_check(self) -> bool:
        """
        Check if Claude Code CLI is available
        """
        try:
            process = await asyncio.create_subprocess_exec(
                "claude", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=10,
            )
            
            return process.returncode == 0
            
        except Exception as e:
            logger.warning("Claude Code health check failed", error=str(e))
            return False
    
    async def _execute_claude_code(self, prompt: str) -> str:
        """
        Execute Claude Code CLI with the given prompt

        Args:
            prompt: The prompt to send to Claude

        Returns:
            Claude's response text

        Raises:
            GenerationError: If execution fails
        """
        # Build command
        # Using --print flag to output directly, -p - to read prompt from stdin
        cmd = [
            "claude",
            "--print",
            "--model", self.model,
            "-p", "-",
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=prompt.encode('utf-8')),
                timeout=self.timeout,
            )
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise GenerationError(f"Claude Code CLI failed: {error_msg}")
            
            return stdout.decode()
            
        except asyncio.TimeoutError:
            raise GenerationError(f"Claude Code CLI timed out after {self.timeout}s")
        except FileNotFoundError:
            raise GenerationError(
                "Claude Code CLI not found. Please install it: npm install -g @anthropic-ai/claude-code"
            )
    
    def _parse_response(
        self,
        response: str,
        topic: str,
        category: Category,
        difficulty: Difficulty,
    ) -> GeneratedContent:
        """
        Parse Claude Code response into GeneratedContent
        """
        try:
            # Try to extract JSON from response
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    raise GenerationError("No JSON found in response")

            data = json.loads(json_str)

            if "title" not in data or "summary" not in data:
                raise GenerationError("Missing required field: title or summary")

            return GeneratedContent(
                title=data["title"],
                category=category,
                difficulty=difficulty,
                summary=data["summary"],
                tags=data.get("tags", []),
            )

        except json.JSONDecodeError as e:
            logger.error("JSON parsing failed", response=response[:500], error=str(e))
            raise GenerationError(f"Failed to parse JSON response: {e}", e)
        except Exception as e:
            if isinstance(e, GenerationError):
                raise
            raise GenerationError(f"Failed to parse response: {e}", e)
