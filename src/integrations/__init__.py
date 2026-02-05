"""
Integrations package for Daily-Bot
External service adapters
"""

from src.integrations.notion import NotionAdapter
from src.integrations.slack import CommandHandler, SlackAdapter

__all__ = [
    "CommandHandler",
    "NotionAdapter",
    "SlackAdapter",
]
