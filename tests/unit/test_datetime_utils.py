"""
Unit tests for datetime utilities
"""

from datetime import datetime, time, timedelta

import pytest

from src.utils.datetime_utils import (
    format_datetime,
    format_time,
    humanize_timedelta,
    parse_time,
)


class TestParseTime:
    """Tests for parse_time function"""

    def test_parse_valid_time(self):
        """Test parsing valid time strings"""
        assert parse_time("07:00") == time(7, 0)
        assert parse_time("19:30") == time(19, 30)
        assert parse_time("00:00") == time(0, 0)
        assert parse_time("23:59") == time(23, 59)

    def test_parse_invalid_time(self):
        """Test parsing invalid time strings"""
        with pytest.raises(ValueError):
            parse_time("25:00")

        with pytest.raises(ValueError):
            parse_time("12:60")

        with pytest.raises(ValueError):
            parse_time("invalid")

        with pytest.raises(ValueError):
            parse_time("12")


class TestFormatTime:
    """Tests for format_time function"""

    def test_format_time(self):
        """Test formatting time objects"""
        assert format_time(time(7, 0)) == "07:00"
        assert format_time(time(19, 30)) == "19:30"
        assert format_time(time(0, 0)) == "00:00"


class TestFormatDatetime:
    """Tests for format_datetime function"""

    def test_format_datetime_with_time(self):
        """Test formatting datetime with time"""
        dt = datetime(2024, 1, 15, 14, 30)
        assert format_datetime(dt) == "2024-01-15 14:30"

    def test_format_datetime_without_time(self):
        """Test formatting datetime without time"""
        dt = datetime(2024, 1, 15, 14, 30)
        assert format_datetime(dt, include_time=False) == "2024-01-15"


class TestHumanizeTimedelta:
    """Tests for humanize_timedelta function"""

    def test_seconds(self):
        """Test humanizing seconds"""
        assert humanize_timedelta(timedelta(seconds=30)) == "30초"

    def test_minutes(self):
        """Test humanizing minutes"""
        assert humanize_timedelta(timedelta(minutes=5)) == "5분"
        assert humanize_timedelta(timedelta(minutes=45)) == "45분"

    def test_hours(self):
        """Test humanizing hours"""
        assert humanize_timedelta(timedelta(hours=2)) == "2시간"
        assert humanize_timedelta(timedelta(hours=2, minutes=30)) == "2시간 30분"

    def test_days(self):
        """Test humanizing days"""
        assert humanize_timedelta(timedelta(days=3)) == "3일"
        assert humanize_timedelta(timedelta(days=1, hours=5)) == "1일 5시간"
