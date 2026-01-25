"""Configuration utilities and environment variables."""

from __future__ import annotations

import os
from pathlib import Path


def _get_project_root() -> Path:
    """Return the project root directory based on this file location."""
    return Path(__file__).resolve().parents[2]


PROJECT_ROOT = _get_project_root()

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
BRONZE_DIR = DATA_DIR / "bronze"
SILVER_DIR = DATA_DIR / "silver"
GOLD_DIR = DATA_DIR / "gold"

RAW_INPUT_FILENAME = os.getenv("RAW_INPUT_FILENAME", "jira_issues_raw.txt")
RAW_INPUT_PATH = PROJECT_ROOT / RAW_INPUT_FILENAME

HOLIDAY_API_URL = os.getenv("HOLIDAY_API_URL", "https://date.nager.at/api/v3/PublicHolidays")
HOLIDAY_COUNTRY_CODE = os.getenv("HOLIDAY_COUNTRY_CODE", "US")

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
AZURE_CONTAINER_NAME = os.getenv("AZURE_CONTAINER_NAME", "")
AZURE_BLOB_NAME = os.getenv("AZURE_BLOB_NAME", "")
