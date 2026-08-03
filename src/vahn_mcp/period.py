"""Shared period-resolution helper."""

from datetime import datetime, timedelta


def resolve_period(period: str) -> tuple[datetime, datetime]:
    """Convert a named period to (start, end) datetime pair."""
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    match period:
        case "today":
            return today_start, now
        case "this_week":
            start = today_start - timedelta(days=today_start.weekday())
            return start, now
        case "this_month":
            return today_start.replace(day=1), now
        case "last_week":
            end = today_start - timedelta(days=today_start.weekday())
            return end - timedelta(days=7), end
        case "last_month":
            first = today_start.replace(day=1)
            end = first - timedelta(seconds=1)
            return end.replace(day=1, hour=0, minute=0, second=0), end
        case _:
            start = today_start - timedelta(days=today_start.weekday())
            return start, now
