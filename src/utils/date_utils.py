"""Date utilities for business day and holiday handling."""

from __future__ import annotations

from datetime import date
from typing import Iterable, Set

import requests

from src.utils.config import HOLIDAY_API_URL, HOLIDAY_COUNTRY_CODE


def fetch_public_holidays(
    year: int,
    country_code: str | None = None,
    api_url: str | None = None,
) -> Set[date]:
    """
    Fetch public holidays for a given year and country.

    TODO: Replace with a more resilient integration (retries, caching).
    """
    base_url = api_url or HOLIDAY_API_URL
    country = country_code or HOLIDAY_COUNTRY_CODE
    url = f"{base_url}/{year}/{country}"

    response = requests.get(url, timeout=30)
    response.raise_for_status()
    holidays = response.json()

    return {date.fromisoformat(item["date"]) for item in holidays}


def is_business_day(check_date: date, holidays: Iterable[date]) -> bool:
    """Return True if the date is a weekday and not a holiday."""
    return check_date.weekday() < 5 and check_date not in set(holidays)
