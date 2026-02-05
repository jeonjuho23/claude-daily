"""
DateTime utilities for Daily-Bot
Handles timezone-aware datetime operations
"""

from datetime import datetime, timedelta, time
from typing import Optional, Tuple
import zoneinfo

from config.settings import settings


def get_timezone() -> zoneinfo.ZoneInfo:
    """Get configured timezone"""
    return zoneinfo.ZoneInfo(settings.timezone)


def now() -> datetime:
    """Get current datetime in configured timezone"""
    return datetime.now(get_timezone())


def today() -> datetime:
    """Get today's date at midnight in configured timezone"""
    return now().replace(hour=0, minute=0, second=0, microsecond=0)


def parse_time(time_str: str) -> time:
    """
    Parse time string (HH:MM) to time object
    
    Args:
        time_str: Time in HH:MM format
        
    Returns:
        time object
        
    Raises:
        ValueError: If format is invalid
    """
    try:
        parts = time_str.split(":")
        if len(parts) != 2:
            raise ValueError(f"Invalid time format: {time_str}")
        return time(hour=int(parts[0]), minute=int(parts[1]))
    except (ValueError, AttributeError) as e:
        raise ValueError(f"Invalid time format: {time_str}. Expected HH:MM") from e


def format_time(t: time) -> str:
    """
    Format time object to HH:MM string
    
    Args:
        t: time object
        
    Returns:
        Formatted time string
    """
    return t.strftime("%H:%M")


def format_datetime(dt: datetime, include_time: bool = True) -> str:
    """
    Format datetime for display
    
    Args:
        dt: datetime object
        include_time: Whether to include time
        
    Returns:
        Formatted datetime string
    """
    if include_time:
        return dt.strftime("%Y-%m-%d %H:%M")
    return dt.strftime("%Y-%m-%d")


def get_next_run_time(schedule_time: str) -> datetime:
    """
    Calculate next run time for a schedule
    
    Args:
        schedule_time: Schedule time in HH:MM format
        
    Returns:
        Next run datetime
    """
    t = parse_time(schedule_time)
    tz = get_timezone()
    current = now()
    
    next_run = current.replace(
        hour=t.hour,
        minute=t.minute,
        second=0,
        microsecond=0,
    )
    
    # If time has passed today, schedule for tomorrow
    if next_run <= current:
        next_run += timedelta(days=1)
    
    return next_run


def get_week_range(reference_date: Optional[datetime] = None) -> Tuple[datetime, datetime]:
    """
    Get start and end of the week containing the reference date
    
    Args:
        reference_date: Reference date (defaults to now)
        
    Returns:
        Tuple of (week_start, week_end)
    """
    ref = reference_date or now()
    
    # Start of week (Monday)
    week_start = ref - timedelta(days=ref.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # End of week (Sunday 23:59:59)
    week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    
    return week_start, week_end


def get_last_week_range() -> Tuple[datetime, datetime]:
    """
    Get start and end of last week
    
    Returns:
        Tuple of (week_start, week_end)
    """
    ref = now() - timedelta(days=7)
    return get_week_range(ref)


def get_month_range(reference_date: Optional[datetime] = None) -> Tuple[datetime, datetime]:
    """
    Get start and end of the month containing the reference date
    
    Args:
        reference_date: Reference date (defaults to now)
        
    Returns:
        Tuple of (month_start, month_end)
    """
    ref = reference_date or now()
    
    # Start of month
    month_start = ref.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # End of month
    if ref.month == 12:
        next_month = ref.replace(year=ref.year + 1, month=1, day=1)
    else:
        next_month = ref.replace(month=ref.month + 1, day=1)
    month_end = next_month - timedelta(seconds=1)
    
    return month_start, month_end


def get_last_month_range() -> Tuple[datetime, datetime]:
    """
    Get start and end of last month
    
    Returns:
        Tuple of (month_start, month_end)
    """
    current = now()
    if current.month == 1:
        ref = current.replace(year=current.year - 1, month=12, day=15)
    else:
        ref = current.replace(month=current.month - 1, day=15)
    return get_month_range(ref)


def is_weekday(day: int, reference_date: Optional[datetime] = None) -> bool:
    """
    Check if reference date matches the specified weekday
    
    Args:
        day: Day of week (0=Monday, 6=Sunday)
        reference_date: Reference date (defaults to now)
        
    Returns:
        True if matches
    """
    ref = reference_date or now()
    return ref.weekday() == day


def is_month_day(day: int, reference_date: Optional[datetime] = None) -> bool:
    """
    Check if reference date matches the specified day of month
    
    Args:
        day: Day of month (1-31)
        reference_date: Reference date (defaults to now)
        
    Returns:
        True if matches
    """
    ref = reference_date or now()
    return ref.day == day


def get_retry_time(attempt: int, base_interval: int = 5) -> datetime:
    """
    Calculate next retry time based on attempt number
    Progressive intervals: 5, 10, 15, 20, 25 minutes
    
    Args:
        attempt: Current attempt number (1-based)
        base_interval: Base interval in minutes
        
    Returns:
        Next retry datetime
    """
    interval_minutes = base_interval * attempt
    return now() + timedelta(minutes=interval_minutes)


def humanize_timedelta(td: timedelta) -> str:
    """
    Convert timedelta to human-readable string
    
    Args:
        td: timedelta object
        
    Returns:
        Human-readable string
    """
    total_seconds = int(td.total_seconds())
    
    if total_seconds < 60:
        return f"{total_seconds}초"
    elif total_seconds < 3600:
        minutes = total_seconds // 60
        return f"{minutes}분"
    elif total_seconds < 86400:
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        if minutes > 0:
            return f"{hours}시간 {minutes}분"
        return f"{hours}시간"
    else:
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        if hours > 0:
            return f"{days}일 {hours}시간"
        return f"{days}일"
