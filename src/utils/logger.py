"""
Logging utilities for Daily-Bot
Using structlog for structured logging
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

import structlog
from structlog.typing import Processor

from config.settings import settings


def setup_logging(
    log_level: Optional[str] = None,
    log_dir: Optional[str] = None,
) -> None:
    """
    Setup structured logging for the application
    
    Args:
        log_level: Override log level from settings
        log_dir: Override log directory
    """
    level = getattr(logging, (log_level or settings.log_level).upper())
    
    # Create log directory
    log_path = Path(log_dir) if log_dir else Path(__file__).parent.parent.parent / "logs"
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Log file with date
    log_file = log_path / f"daily_bot_{datetime.now().strftime('%Y%m%d')}.log"
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        level=level,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )
    
    # Shared processors
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]
    
    # Configure structlog
    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a named logger instance
    
    Args:
        name: Logger name (usually module name)
        
    Returns:
        Configured logger instance
    """
    return structlog.get_logger(name)


def cleanup_old_logs(retention_days: Optional[int] = None) -> int:
    """
    Clean up log files older than retention period
    
    Args:
        retention_days: Override retention period from settings
        
    Returns:
        Number of files deleted
    """
    days = retention_days or settings.log_retention_days
    log_path = Path(__file__).parent.parent.parent / "logs"
    
    if not log_path.exists():
        return 0
    
    deleted_count = 0
    cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
    
    for log_file in log_path.glob("daily_bot_*.log"):
        if log_file.stat().st_mtime < cutoff_date:
            log_file.unlink()
            deleted_count += 1
    
    return deleted_count


class LogContext:
    """Context manager for adding temporary log context"""
    
    def __init__(self, **kwargs):
        self.context = kwargs
        self._token = None
    
    def __enter__(self):
        self._token = structlog.contextvars.bind_contextvars(**self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._token:
            structlog.contextvars.unbind_contextvars(*self.context.keys())
        return False
