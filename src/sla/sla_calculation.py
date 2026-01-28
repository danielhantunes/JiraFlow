"""SLA calculation utilities."""

from __future__ import annotations

from datetime import datetime, timedelta, time, date
from typing import Iterable, Set


def calculate_business_hours(
    start_dt: datetime,
    end_dt: datetime,
    holidays: Iterable[date],
    business_start: time = time(9, 0),
    business_end: time = time(17, 0),
) -> float:
    """
    Calculate business hours between two datetimes.

    TODO: Adjust for timezones and custom business calendars if required.
    """
    if end_dt <= start_dt:
        return 0.0

    holidays_set: Set[date] = set(holidays)
    total_hours = 0.0
    current = start_dt

    while current.date() <= end_dt.date():
        is_weekday = current.weekday() < 5
        is_holiday = current.date() in holidays_set
        if is_weekday and not is_holiday:
            day_start = datetime.combine(current.date(), business_start)
            day_end = datetime.combine(current.date(), business_end)
            interval_start = max(current, day_start)
            interval_end = min(end_dt, day_end)
            if interval_end > interval_start:
                total_hours += (interval_end - interval_start).total_seconds() / 3600
        # Move to the next day boundary.
        current = datetime.combine(current.date(), time(0, 0)) + timedelta(days=1)

    return round(total_hours, 2)


def get_expected_sla_hours(priority: str) -> int:
    """
    Return expected SLA hours based on priority.

    TODO: Replace with business-approved SLA matrix.
    """
    mapping = {
        "Highest": 8,
        "High": 16,
        "Medium": 24,
        "Low": 40,
        "Lowest": 80,
    }
    return mapping.get(priority, 24)


def get_sla_status(actual_hours: float, expected_hours: int) -> str:
    """Return SLA status (met/violated)."""
    return "met" if actual_hours <= expected_hours else "violated"
