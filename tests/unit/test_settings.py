"""
Unit tests for config/settings.py
"""

import pytest
from pydantic import ValidationError


class TestSettingsValidators:
    """Tests for Settings field validators"""

    def test_valid_time_format(self, mock_settings):
        """Valid time format should pass"""
        # Clear lru_cache
        from config.settings import Settings, get_settings

        get_settings.cache_clear()

        settings = Settings(_env_file=".env.example")
        assert settings.default_schedule_time == "07:00"

    def test_invalid_time_format_raises(self, mock_settings, monkeypatch):
        """Invalid time format should raise ValidationError"""
        from config.settings import Settings, get_settings

        get_settings.cache_clear()

        monkeypatch.setenv("DEFAULT_SCHEDULE_TIME", "25:00")

        with pytest.raises(ValidationError):
            Settings(_env_file=".env.example")

    def test_invalid_time_format_no_colon(self, mock_settings, monkeypatch):
        """Time without colon should raise ValidationError"""
        from config.settings import Settings, get_settings

        get_settings.cache_clear()

        monkeypatch.setenv("DEFAULT_SCHEDULE_TIME", "0700")

        with pytest.raises(ValidationError):
            Settings(_env_file=".env.example")

    def test_valid_weekday(self, mock_settings):
        """Valid weekday (0-6) should pass"""
        from config.settings import Settings, get_settings

        get_settings.cache_clear()

        settings = Settings(_env_file=".env.example")
        assert 0 <= settings.weekly_report_day <= 6

    def test_invalid_weekday_raises(self, mock_settings, monkeypatch):
        """Invalid weekday should raise ValidationError"""
        from config.settings import Settings, get_settings

        get_settings.cache_clear()

        monkeypatch.setenv("WEEKLY_REPORT_DAY", "7")

        with pytest.raises(ValidationError):
            Settings(_env_file=".env.example")

    def test_valid_monthday(self, mock_settings):
        """Valid month day (1-28) should pass"""
        from config.settings import Settings, get_settings

        get_settings.cache_clear()

        settings = Settings(_env_file=".env.example")
        assert 1 <= settings.monthly_report_day <= 28

    def test_invalid_monthday_raises(self, mock_settings, monkeypatch):
        """Invalid month day should raise ValidationError"""
        from config.settings import Settings, get_settings

        get_settings.cache_clear()

        monkeypatch.setenv("MONTHLY_REPORT_DAY", "29")

        with pytest.raises(ValidationError):
            Settings(_env_file=".env.example")


class TestSettingsProperties:
    """Tests for Settings properties"""

    def test_report_channel_uses_report_channel_id(self, mock_settings, monkeypatch):
        """report_channel should use slack_report_channel_id if set"""
        from config.settings import Settings, get_settings

        get_settings.cache_clear()

        monkeypatch.setenv("SLACK_REPORT_CHANNEL_ID", "C_REPORT_123")

        settings = Settings(_env_file=".env.example")
        assert settings.report_channel == "C_REPORT_123"

    def test_report_channel_fallback_to_main(self, mock_settings):
        """report_channel should fallback to main channel if report not set"""
        from config.settings import Settings, get_settings

        get_settings.cache_clear()

        settings = Settings(_env_file=".env.example")
        assert settings.report_channel == settings.slack_channel_id

    def test_notion_enabled_true(self, mock_settings):
        """notion_enabled should be True when both keys are set"""
        from config.settings import Settings, get_settings

        get_settings.cache_clear()

        settings = Settings(_env_file=".env.example")
        assert settings.notion_enabled is True

    def test_notion_enabled_false_no_keys(self, mock_settings, monkeypatch):
        """notion_enabled should be False when Notion keys are None"""
        from config.settings import Settings, get_settings

        get_settings.cache_clear()

        monkeypatch.delenv("NOTION_API_KEY", raising=False)
        monkeypatch.delenv("NOTION_DATABASE_ID", raising=False)

        settings = Settings(_env_file=".env.example")
        assert settings.notion_api_key is None
        assert settings.notion_database_id is None
        assert settings.notion_enabled is False

    def test_notion_enabled_false_empty_strings(self, mock_settings, monkeypatch):
        """notion_enabled should be False when Notion keys are empty strings"""
        from config.settings import Settings, get_settings

        get_settings.cache_clear()

        monkeypatch.setenv("NOTION_API_KEY", "")
        monkeypatch.setenv("NOTION_DATABASE_ID", "")

        settings = Settings(_env_file=".env.example")
        assert settings.notion_enabled is False

    def test_notion_enabled_false_partial_no_db_id(self, mock_settings, monkeypatch):
        """notion_enabled should be False when only api_key is set"""
        from config.settings import Settings, get_settings

        get_settings.cache_clear()

        monkeypatch.setenv("NOTION_DATABASE_ID", "")

        settings = Settings(_env_file=".env.example")
        assert settings.notion_enabled is False

    def test_notion_enabled_false_partial_no_api_key(self, mock_settings, monkeypatch):
        """notion_enabled should be False when only database_id is set"""
        from config.settings import Settings, get_settings

        get_settings.cache_clear()

        monkeypatch.setenv("NOTION_API_KEY", "")

        settings = Settings(_env_file=".env.example")
        assert settings.notion_enabled is False


class TestLazySettings:
    """Tests for _LazySettings proxy"""

    def test_lazy_loading_defers_validation(self, monkeypatch):
        """_LazySettings should not validate until first access"""
        # This test verifies that importing settings doesn't immediately fail
        # even if env vars are missing
        from config.settings import _LazySettings

        # Create new lazy settings without validation
        lazy = _LazySettings()
        # Just creating it shouldn't raise - only accessing attributes should

    def test_lazy_settings_getattr(self, mock_settings):
        """_LazySettings should proxy attribute access"""
        from config.settings import _LazySettings, get_settings

        get_settings.cache_clear()

        lazy = _LazySettings()
        # Access should work after env is set
        assert lazy.timezone == "Asia/Seoul"

    def test_lazy_settings_setattr(self, mock_settings):
        """_LazySettings should proxy attribute setting"""
        from config.settings import _LazySettings, get_settings

        get_settings.cache_clear()

        lazy = _LazySettings()
        # Force initialization
        _ = lazy.timezone

        # Setting attribute should work
        lazy.log_level = "DEBUG"
        assert lazy.log_level == "DEBUG"


class TestGetSettings:
    """Tests for get_settings function"""

    def test_returns_settings_instance(self, mock_settings):
        """get_settings should return Settings instance"""
        from config.settings import Settings, get_settings

        get_settings.cache_clear()

        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_caching_returns_same_instance(self, mock_settings):
        """get_settings should return cached instance"""
        from config.settings import get_settings

        get_settings.cache_clear()

        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2


class TestSettingsDefaults:
    """Tests for Settings default values"""

    def test_default_values(self, mock_settings):
        """Verify default values are set correctly"""
        from config.settings import Settings, get_settings

        get_settings.cache_clear()

        settings = Settings(_env_file=".env.example")

        assert settings.default_schedule_time == "07:00"
        assert settings.timezone == "Asia/Seoul"
        assert settings.language == "ko"
        assert settings.log_level == "INFO"
        assert settings.log_retention_days == 90
        assert settings.max_retries == 5
        assert settings.retry_base_interval == 5
        assert settings.db_path == "data/daily_bot.db"
