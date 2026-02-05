"""
Error handling and retry logic for Daily-Bot
"""

import asyncio
from datetime import datetime
from typing import Optional, Callable, Awaitable, Any, Dict

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryError,
)

from src.domain.models import ExecutionLog
from src.domain.enums import ExecutionStatus
from src.utils.logger import get_logger
from src.utils.datetime_utils import get_retry_time
from config.settings import settings

logger = get_logger(__name__)


class RetryableError(Exception):
    """Error that can be retried"""
    pass


class NonRetryableError(Exception):
    """Error that should not be retried"""
    pass


class ErrorHandler:
    """
    Handles errors and retry logic for Daily-Bot
    
    Implements progressive retry intervals:
    - Attempt 1: 5 minutes
    - Attempt 2: 10 minutes
    - Attempt 3: 15 minutes
    - Attempt 4: 20 minutes
    - Attempt 5: 25 minutes (final)
    """
    
    def __init__(
        self,
        max_retries: Optional[int] = None,
        base_interval: Optional[int] = None,
        on_error_callback: Optional[Callable[[str, Dict[str, Any]], Awaitable[None]]] = None,
    ):
        """
        Initialize error handler
        
        Args:
            max_retries: Maximum retry attempts
            base_interval: Base interval in minutes
            on_error_callback: Async callback for error notifications
        """
        self.max_retries = max_retries or settings.max_retries
        self.base_interval = base_interval or settings.retry_base_interval
        self.on_error_callback = on_error_callback
    
    def create_retry_decorator(
        self,
        max_attempts: Optional[int] = None,
    ):
        """
        Create a retry decorator with configured settings
        
        Args:
            max_attempts: Override max attempts
            
        Returns:
            Tenacity retry decorator
        """
        attempts = max_attempts or self.max_retries
        
        return retry(
            stop=stop_after_attempt(attempts),
            wait=wait_exponential(multiplier=self.base_interval * 60, min=60, max=30 * 60),
            retry=retry_if_exception_type(RetryableError),
            reraise=True,
        )
    
    async def execute_with_retry(
        self,
        func: Callable[..., Awaitable[Any]],
        *args,
        execution_log: Optional[ExecutionLog] = None,
        update_log_callback: Optional[Callable[[ExecutionLog], Awaitable[None]]] = None,
        **kwargs,
    ) -> Any:
        """
        Execute a function with retry logic
        
        Args:
            func: Async function to execute
            *args: Function arguments
            execution_log: Optional execution log to update
            update_log_callback: Callback to update execution log
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If all retries fail
        """
        attempt = 0
        last_error = None
        
        while attempt < self.max_retries:
            attempt += 1
            
            # Update execution log
            if execution_log:
                execution_log.attempt_count = attempt
                execution_log.status = ExecutionStatus.RUNNING if attempt == 1 else ExecutionStatus.RETRY
                if update_log_callback:
                    await update_log_callback(execution_log)
            
            try:
                logger.info(
                    "Executing with retry",
                    attempt=attempt,
                    max_retries=self.max_retries,
                )
                
                result = await func(*args, **kwargs)
                
                # Success
                if execution_log:
                    execution_log.status = ExecutionStatus.SUCCESS
                    execution_log.completed_at = datetime.now()
                    if update_log_callback:
                        await update_log_callback(execution_log)
                
                return result
                
            except NonRetryableError as e:
                # Don't retry
                logger.error(
                    "Non-retryable error occurred",
                    error=str(e),
                    attempt=attempt,
                )
                last_error = e
                break
                
            except Exception as e:
                last_error = e
                logger.warning(
                    "Attempt failed",
                    error=str(e),
                    attempt=attempt,
                    max_retries=self.max_retries,
                )
                
                if execution_log:
                    execution_log.error_message = str(e)
                    if update_log_callback:
                        await update_log_callback(execution_log)
                
                if attempt < self.max_retries:
                    # Calculate wait time
                    wait_seconds = self.base_interval * attempt * 60
                    logger.info(
                        "Waiting before retry",
                        wait_seconds=wait_seconds,
                        next_attempt=attempt + 1,
                    )
                    await asyncio.sleep(wait_seconds)
        
        # All retries exhausted
        if execution_log:
            execution_log.status = ExecutionStatus.FAILED
            execution_log.completed_at = datetime.now()
            execution_log.error_message = str(last_error) if last_error else "Unknown error"
            if update_log_callback:
                await update_log_callback(execution_log)
        
        # Notify about failure
        if self.on_error_callback and last_error:
            await self.on_error_callback(
                str(last_error),
                {
                    "attempts": attempt,
                    "max_retries": self.max_retries,
                    "function": func.__name__,
                }
            )
        
        raise last_error if last_error else Exception("All retries failed")
    
    def calculate_next_retry_time(self, attempt: int) -> datetime:
        """
        Calculate the next retry time
        
        Args:
            attempt: Current attempt number
            
        Returns:
            Datetime for next retry
        """
        return get_retry_time(attempt, self.base_interval)
    
    def should_retry(self, attempt: int, error: Exception) -> bool:
        """
        Determine if an error should be retried
        
        Args:
            attempt: Current attempt number
            error: The exception that occurred
            
        Returns:
            True if should retry
        """
        if attempt >= self.max_retries:
            return False
        
        if isinstance(error, NonRetryableError):
            return False
        
        # Retry for common transient errors
        retryable_messages = [
            "timeout",
            "connection",
            "rate limit",
            "temporarily",
            "503",
            "502",
            "500",
        ]
        
        error_str = str(error).lower()
        return any(msg in error_str for msg in retryable_messages) or isinstance(error, RetryableError)


def is_retryable_error(error: Exception) -> bool:
    """
    Helper function to check if an error is retryable
    
    Args:
        error: Exception to check
        
    Returns:
        True if retryable
    """
    if isinstance(error, NonRetryableError):
        return False
    
    if isinstance(error, RetryableError):
        return True
    
    # Check for common transient errors
    error_str = str(error).lower()
    retryable_indicators = [
        "timeout",
        "connection refused",
        "connection reset",
        "rate limit",
        "too many requests",
        "service unavailable",
        "bad gateway",
        "internal server error",
        "temporarily unavailable",
    ]
    
    return any(indicator in error_str for indicator in retryable_indicators)
