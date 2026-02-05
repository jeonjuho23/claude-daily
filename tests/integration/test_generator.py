"""
Integration tests for src/generators/claude_code_generator.py
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.domain.enums import Category, Difficulty
from src.domain.models import GeneratedContent
from src.generators.base import GenerationError
from src.generators.claude_code_generator import ClaudeCodeGenerator


@pytest.fixture
def generator():
    return ClaudeCodeGenerator(timeout=180)


def _make_mock_process(stdout="", stderr="", returncode=0):
    """Helper to create mock subprocess"""
    process = AsyncMock()
    process.communicate = AsyncMock(return_value=(stdout.encode("utf-8"), stderr.encode("utf-8")))
    process.returncode = returncode
    return process


class TestGenerate:
    @pytest.mark.asyncio
    @patch("src.generators.claude_code_generator.asyncio.create_subprocess_exec")
    async def test_parses_json_in_markdown_block(self, mock_exec, generator):
        data = {"title": "Test Title", "summary": "Test summary", "tags": ["t1"]}
        stdout = f"Some text\n```json\n{json.dumps(data)}\n```\nMore text"
        mock_exec.return_value = _make_mock_process(stdout=stdout)

        result = await generator.generate("Test", Category.NETWORK, Difficulty.INTERMEDIATE)
        assert isinstance(result, GeneratedContent)
        assert result.title == "Test Title"
        assert result.summary == "Test summary"

    @pytest.mark.asyncio
    @patch("src.generators.claude_code_generator.asyncio.create_subprocess_exec")
    async def test_parses_raw_json(self, mock_exec, generator):
        data = {"title": "Raw Title", "summary": "Raw summary", "tags": []}
        stdout = json.dumps(data)
        mock_exec.return_value = _make_mock_process(stdout=stdout)

        result = await generator.generate("Test", Category.NETWORK, Difficulty.BEGINNER)
        assert result.title == "Raw Title"

    @pytest.mark.asyncio
    @patch("src.generators.claude_code_generator.asyncio.create_subprocess_exec")
    async def test_raises_on_no_json_found(self, mock_exec, generator):
        mock_exec.return_value = _make_mock_process(stdout="no json here")

        with pytest.raises(GenerationError, match="No JSON found"):
            await generator.generate("Test", Category.NETWORK)

    @pytest.mark.asyncio
    @patch("src.generators.claude_code_generator.asyncio.create_subprocess_exec")
    async def test_raises_on_invalid_json(self, mock_exec, generator):
        mock_exec.return_value = _make_mock_process(stdout="```json\n{invalid}\n```")

        with pytest.raises(GenerationError, match="parse"):
            await generator.generate("Test", Category.NETWORK)

    @pytest.mark.asyncio
    @patch("src.generators.claude_code_generator.asyncio.create_subprocess_exec")
    async def test_raises_on_missing_title(self, mock_exec, generator):
        data = {"summary": "no title"}
        mock_exec.return_value = _make_mock_process(stdout=json.dumps(data))

        with pytest.raises(GenerationError, match="Missing required"):
            await generator.generate("Test", Category.NETWORK)

    @pytest.mark.asyncio
    @patch("src.generators.claude_code_generator.asyncio.create_subprocess_exec")
    async def test_raises_on_missing_summary(self, mock_exec, generator):
        data = {"title": "no summary"}
        mock_exec.return_value = _make_mock_process(stdout=json.dumps(data))

        with pytest.raises(GenerationError, match="Missing required"):
            await generator.generate("Test", Category.NETWORK)

    @pytest.mark.asyncio
    @patch("src.generators.claude_code_generator.asyncio.create_subprocess_exec")
    async def test_raises_on_cli_timeout(self, mock_exec, generator):
        process = AsyncMock()
        process.communicate = AsyncMock(side_effect=TimeoutError())
        mock_exec.return_value = process

        with pytest.raises(GenerationError, match="timed out"):
            await generator.generate("Test", Category.NETWORK)

    @pytest.mark.asyncio
    @patch("src.generators.claude_code_generator.asyncio.create_subprocess_exec")
    async def test_raises_on_cli_not_found(self, mock_exec, generator):
        mock_exec.side_effect = FileNotFoundError()

        with pytest.raises(GenerationError, match="not found"):
            await generator.generate("Test", Category.NETWORK)

    @pytest.mark.asyncio
    @patch("src.generators.claude_code_generator.asyncio.create_subprocess_exec")
    async def test_raises_on_nonzero_returncode(self, mock_exec, generator):
        mock_exec.return_value = _make_mock_process(stderr="Error!", returncode=1)

        with pytest.raises(GenerationError, match="CLI failed"):
            await generator.generate("Test", Category.NETWORK)


class TestGenerateRandom:
    @pytest.mark.asyncio
    @patch("src.generators.claude_code_generator.asyncio.create_subprocess_exec")
    async def test_selects_unused_topic(self, mock_exec, generator):
        data = {"title": "Random", "summary": "Summary", "tags": []}
        mock_exec.return_value = _make_mock_process(stdout=json.dumps(data))

        result = await generator.generate_random(used_topics=[])
        assert isinstance(result, GeneratedContent)

    @pytest.mark.asyncio
    async def test_raises_when_all_used(self, generator):
        from config.topics import get_all_topics

        all_topics = [t[1] for t in get_all_topics()]

        with pytest.raises(GenerationError):
            await generator.generate_random(used_topics=all_topics)

    @pytest.mark.asyncio
    @patch("src.generators.claude_code_generator.asyncio.create_subprocess_exec")
    async def test_preferred_category(self, mock_exec, generator):
        data = {"title": "Network Topic", "summary": "Summary", "tags": []}
        mock_exec.return_value = _make_mock_process(stdout=json.dumps(data))

        result = await generator.generate_random(
            used_topics=[], preferred_category=Category.NETWORK
        )
        assert isinstance(result, GeneratedContent)


class TestHealthCheck:
    @pytest.mark.asyncio
    @patch("src.generators.claude_code_generator.asyncio.create_subprocess_exec")
    async def test_returns_true_on_success(self, mock_exec, generator):
        mock_exec.return_value = _make_mock_process(stdout="claude 1.0.0")

        result = await generator.health_check()
        assert result is True

    @pytest.mark.asyncio
    @patch("src.generators.claude_code_generator.asyncio.create_subprocess_exec")
    async def test_returns_false_on_failure(self, mock_exec, generator):
        mock_exec.side_effect = FileNotFoundError()

        result = await generator.health_check()
        assert result is False

    @pytest.mark.asyncio
    @patch("src.generators.claude_code_generator.asyncio.create_subprocess_exec")
    async def test_returns_false_on_timeout(self, mock_exec, generator):
        process = AsyncMock()
        process.communicate = AsyncMock(side_effect=TimeoutError())
        mock_exec.return_value = process

        result = await generator.health_check()
        assert result is False


class TestParseResponse:
    def test_parses_valid_json_in_codeblock(self, generator):
        data = {"title": "Title", "summary": "Sum", "tags": ["a"]}
        response = f"```json\n{json.dumps(data)}\n```"
        result = generator._parse_response(
            response, "Test", Category.NETWORK, Difficulty.INTERMEDIATE
        )
        assert result.title == "Title"
        assert result.tags == ["a"]

    def test_parses_raw_json(self, generator):
        data = {"title": "Title2", "summary": "Sum2"}
        response = json.dumps(data)
        result = generator._parse_response(response, "Test", Category.OS, Difficulty.BEGINNER)
        assert result.title == "Title2"

    def test_raises_on_no_json(self, generator):
        with pytest.raises(GenerationError):
            generator._parse_response("no json", "T", Category.NETWORK, Difficulty.INTERMEDIATE)

    def test_raises_on_missing_fields(self, generator):
        data = {"title": "only title"}
        with pytest.raises(GenerationError):
            generator._parse_response(
                json.dumps(data), "T", Category.NETWORK, Difficulty.INTERMEDIATE
            )

    def test_parse_response_with_multiple_json_blocks(self, generator):
        """Should capture the first valid JSON block, not merge all blocks"""
        response = 'prefix {"title":"A","summary":"S","tags":[]} extra {"other":"json"}'
        content = generator._parse_response(
            response, "topic", Category.ALGORITHM, Difficulty.INTERMEDIATE
        )
        assert content.title == "A"
        assert content.summary == "S"

    def test_parse_response_with_nested_json(self, generator):
        """Should handle nested JSON objects correctly"""
        data = {"title": "Nested", "summary": "Sum", "tags": [], "meta": {"key": "val"}}
        response = f"Here is the result: {json.dumps(data)} done."
        content = generator._parse_response(
            response, "topic", Category.NETWORK, Difficulty.ADVANCED
        )
        assert content.title == "Nested"
        assert content.summary == "Sum"
