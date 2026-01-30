"""Date utilities for business day and holiday handling."""

from __future__ import annotations

from datetime import date
import json
from typing import Iterable, Set
from pathlib import Path
from urllib.request import urlopen

from src.utils.config import (
    DEFAULT_HOLIDAY_YEAR,
    HOLIDAY_API_URL,
    HOLIDAY_COUNTRY_CODE,
    REFERENCE_DIR,
)


def fetch_public_holidays(
    year: int | None = None,
    country_code: str | None = None,
    api_url: str | None = None,
) -> Set[date]:
    """
    Fetch public holidays for a given year and country.

    TODO: Replace with a more resilient integration (retries, caching).
    """
    # Build URL for the Nager public holidays API.
    base_url = api_url or HOLIDAY_API_URL
    country = country_code or HOLIDAY_COUNTRY_CODE
    holiday_year = year if year is not None else DEFAULT_HOLIDAY_YEAR
    url = f"{base_url}/{holiday_year}/{country}"

    cache_path = REFERENCE_DIR / f"holidays_{country}_{holiday_year}.json"
    if cache_path.exists():
        payload = cache_path.read_text(encoding="utf-8")
    else:
        # Simple HTTP fetch using stdlib to avoid extra dependencies.
        with urlopen(url, timeout=30) as response:
            payload = response.read().decode("utf-8")
        REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(payload, encoding="utf-8")

    holidays = json.loads(payload)

    filtered = [
        item
        for item in holidays
        if item.get("counties") is None and "Public" in (item.get("types") or [])
    ]

    return {date.fromisoformat(item["date"]) for item in filtered}


def is_business_day(check_date: date, holidays: Iterable[date]) -> bool:
    """Return True if the date is a weekday and not a holiday."""
    return check_date.weekday() < 5 and check_date not in set(holidays)
