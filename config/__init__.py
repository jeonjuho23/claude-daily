"""
Configuration package for Daily-Bot
"""

from config.settings import Settings, get_settings, settings
from config.topics import (
    CATEGORIES,
    TOPICS,
    get_all_topics,
    get_category_name,
    get_topics_by_category,
    get_total_topic_count,
)

__all__ = [
    "CATEGORIES",
    "TOPICS",
    "Settings",
    "get_all_topics",
    "get_category_name",
    "get_settings",
    "get_topics_by_category",
    "get_total_topic_count",
    "settings",
]
