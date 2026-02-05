"""
Configuration package for Daily-Bot
"""

from config.settings import Settings, get_settings, settings
from config.topics import (
    CATEGORIES,
    TOPICS,
    get_all_topics,
    get_topics_by_category,
    get_category_name,
    get_total_topic_count,
)

__all__ = [
    "Settings",
    "get_settings",
    "settings",
    "CATEGORIES",
    "TOPICS",
    "get_all_topics",
    "get_topics_by_category",
    "get_category_name",
    "get_total_topic_count",
]
