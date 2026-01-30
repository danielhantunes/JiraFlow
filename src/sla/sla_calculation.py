"""SLA calculation utilities."""

from __future__ import annotations

from datetime import datetime, timedelta, time, date
from typing import Iterable, Set


def calculate_business_hours(
    start_dt: datetime,
    end_dt: datetime,
    holidays: Iterable[date],
    business_start: time = time(0, 0),
    business_end: time = time(23, 59, 59),
) -> float:
    """
    Calculate business hours between two datetimes.

    Uses a 24-hour business day and excludes weekends/holidays.
    """
    if end_dt <= start_dt:
        return 0.0

    holidays_set: Set[date] = set(holidays)
    total_hours = 0.0
    current = start_dt

    # Preserve timezone awareness when constructing day boundaries.
    tzinfo = start_dt.tzinfo or end_dt.tzinfo

    # Iterate day by day, only counting intervals on business days.
    while current.date() <= end_dt.date():
        is_weekday = current.weekday() < 5
        is_holiday = current.date() in holidays_set
        if is_weekday and not is_holiday:
            day_start = datetime.combine(current.date(), business_start, tzinfo=tzinfo)
            day_end = datetime.combine(current.date(), business_end, tzinfo=tzinfo)
            interval_start = max(current, day_start)
            interval_end = min(end_dt, day_end)
            if interval_end > interval_start:
                total_hours += (interval_end - interval_start).total_seconds() / 3600
        # Move to the next day boundary.
        current = datetime.combine(current.date(), time(0, 0), tzinfo=tzinfo) + timedelta(days=1)

    return round(total_hours, 2)


def get_expected_sla_hours(priority: str) -> int:
    """
    Return expected SLA hours based on priority.
    """
    mapping = {
        "High": 24,
        "Medium": 72,
        "Low": 120,
    }
    return mapping.get(priority, 72)


def get_sla_status(actual_hours: float, expected_hours: int) -> str:
    """Return SLA status (met/violated)."""
    return "met" if actual_hours <= expected_hours else "violated"
