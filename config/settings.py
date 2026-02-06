"""
Configuration management for Daily-Bot
Uses Pydantic Settings for type-safe configuration
"""

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Slack Configuration
    slack_bot_token: str = Field(..., description="Slack Bot OAuth Token")
    slack_signing_secret: str = Field(..., description="Slack Signing Secret")
    slack_app_token: str = Field(..., description="Slack App-Level Token")
    slack_channel_id: str = Field(..., description="Main channel for content")
    slack_report_channel_id: str | None = Field(None, description="Channel for reports")

    # Notion Configuration (Optional)
    notion_api_key: str | None = Field(None, description="Notion Integration API Key")
    notion_database_id: str | None = Field(None, description="Notion Database ID for content")
    notion_report_page_id: str | None = Field(None, description="Notion Page ID for reports")

    # Schedule Configuration
    default_schedule_time: str = Field("07:00", description="Default schedule time (HH:MM)")
    timezone: str = Field("Asia/Seoul", description="Timezone for scheduling")

    # Bot Configuration
    bot_owner_name: str = Field("User", description="Bot owner name")
    language: str = Field("ko", description="Language (ko, en)")
    log_level: str = Field("INFO", description="Logging level")
    log_retention_days: int = Field(90, description="Log retention period in days")

    # Retry Configuration
    max_retries: int = Field(5, description="Maximum retry attempts")
    retry_base_interval: int = Field(5, description="Base retry interval in minutes")

    # Report Configuration
    weekly_report_day: int = Field(0, description="Day of week for weekly report (0=Mon)")
    weekly_report_time: str = Field("10:00", description="Time for weekly report")
    monthly_report_day: int = Field(1, description="Day of month for monthly report")
    monthly_report_time: str = Field("10:00", description="Time for monthly report")

    # Database
    db_path: str = Field("data/daily_bot.db", description="SQLite database path")

    # Rate Limiting
    slack_rate_limit: int = Field(50, description="Slack API requests per minute")
    notion_rate_limit: float = Field(2.5, description="Notion API requests per second")

    @field_validator("default_schedule_time", "weekly_report_time", "monthly_report_time")
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        """Validate time format (HH:MM)"""
        try:
            parts = v.split(":")
            if len(parts) != 2:
                raise ValueError
            hour, minute = int(parts[0]), int(parts[1])
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError
        except (ValueError, AttributeError):
            raise ValueError(f"Invalid time format: {v}. Expected HH:MM (24-hour)")
        return v

    @field_validator("weekly_report_day")
    @classmethod
    def validate_weekday(cls, v: int) -> int:
        """Validate weekday (0-6)"""
        if not 0 <= v <= 6:
            raise ValueError(f"Invalid weekday: {v}. Expected 0-6 (Monday-Sunday)")
        return v

    @field_validator("monthly_report_day")
    @classmethod
    def validate_monthday(cls, v: int) -> int:
        """Validate day of month (1-28)"""
        if not 1 <= v <= 28:
            raise ValueError(f"Invalid day of month: {v}. Expected 1-28")
        return v

    @property
    def report_channel(self) -> str:
        """Get report channel, fallback to main channel"""
        return self.slack_report_channel_id or self.slack_channel_id

    @property
    def notion_enabled(self) -> bool:
        """Check if Notion integration is configured"""
        return bool(self.notion_api_key and self.notion_database_id)

    def get_db_full_path(self) -> Path:
        """Get full path to database file"""
        path = Path(self.db_path)
        if not path.is_absolute():
            # Relative to project root
            path = Path(__file__).parent.parent / path
        return path


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


class _LazySettings:
    """Lazy proxy that defers validation until first access"""

    _instance: Settings | None = None

    def __getattr__(self, name: str) -> Any:
        if self._instance is None:
            self._instance = get_settings()
        return getattr(self._instance, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "_instance":
            object.__setattr__(self, name, value)
        else:
            if self._instance is None:
                self._instance = get_settings()
            setattr(self._instance, name, value)


# Export lazy settings instance for easy import
settings = _LazySettings()
