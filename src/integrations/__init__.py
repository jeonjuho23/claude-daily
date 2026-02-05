"""
Integrations package for Daily-Bot
External service adapters
"""

from src.integrations.slack import SlackAdapter, CommandHandler
from src.integrations.notion import NotionAdapter

__all__ = [
    "SlackAdapter",
    "CommandHandler",
    "NotionAdapter",
]
