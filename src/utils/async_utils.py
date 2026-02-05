"""
Async utilities for Daily-Bot
Provides safe background task creation with exception handling
"""

import asyncio
from typing import Callable, Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


def create_background_task(
    coro,
    *,
    context: str = "",
    on_error: Optional[Callable[[Exception], None]] = None,
) -> asyncio.Task:
    """
    Create asyncio task with automatic exception handling

    Args:
        coro: Coroutine to run as a task
        context: Description of the task for logging
        on_error: Optional callback to invoke on error

    Returns:
        The created asyncio.Task
    """
    task = asyncio.create_task(coro)

    def handle_exception(t: asyncio.Task):
        try:
            exc = t.exception()
            if exc:
                logger.error(f"Background task failed: {context}", error=str(exc))
                if on_error:
                    on_error(exc)
        except asyncio.CancelledError:
            pass

    task.add_done_callback(handle_exception)
    return task
