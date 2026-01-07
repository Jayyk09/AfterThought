"""Date and time utilities for podcast episodes."""

from datetime import datetime, timedelta
from typing import Optional


# Core Data reference date: January 1, 2001 00:00:00 UTC
CORE_DATA_EPOCH = datetime(2001, 1, 1, 0, 0, 0)


def core_data_to_datetime(timestamp: Optional[float]) -> Optional[datetime]:
    """
    Convert Core Data timestamp to Python datetime.

    Core Data timestamps are seconds since January 1, 2001 00:00:00 UTC.

    Args:
        timestamp: Core Data timestamp (seconds since 2001-01-01)

    Returns:
        Python datetime object, or None if timestamp is None
    """
    if timestamp is None or timestamp == 0:
        return None

    return CORE_DATA_EPOCH + timedelta(seconds=timestamp)


def datetime_to_core_data(dt: datetime) -> float:
    """
    Convert Python datetime to Core Data timestamp.

    Args:
        dt: Python datetime object

    Returns:
        Core Data timestamp (seconds since 2001-01-01)
    """
    delta = dt - CORE_DATA_EPOCH
    return delta.total_seconds()


def format_duration(seconds: int) -> str:
    """
    Format duration in seconds to HH:MM:SS or MM:SS.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string
    """
    if seconds <= 0:
        return "0:00"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_relative_time(dt: datetime) -> str:
    """
    Format datetime as relative time (e.g., "2 days ago").

    Args:
        dt: Datetime to format

    Returns:
        Relative time string
    """
    if dt is None:
        return "Never"

    now = datetime.now()
    delta = now - dt

    if delta < timedelta(minutes=1):
        return "Just now"
    elif delta < timedelta(hours=1):
        minutes = int(delta.total_seconds() / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif delta < timedelta(days=1):
        hours = int(delta.total_seconds() / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif delta < timedelta(days=7):
        days = delta.days
        return f"{days} day{'s' if days != 1 else ''} ago"
    elif delta < timedelta(days=30):
        weeks = delta.days // 7
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"
    elif delta < timedelta(days=365):
        months = delta.days // 30
        return f"{months} month{'s' if months != 1 else ''} ago"
    else:
        years = delta.days // 365
        return f"{years} year{'s' if years != 1 else ''} ago"
