"""Configuration utilities and environment variables."""

from __future__ import annotations

import os
from pathlib import Path


def _get_project_root() -> Path:
    """Return the project root directory based on this file location."""
    # Keep project-relative paths stable regardless of CWD.
    return Path(__file__).resolve().parents[2]


PROJECT_ROOT = _get_project_root()

def _load_env_file(env_path: Path) -> None:
    """Load key=value pairs from a .env file using stdlib only."""
    if not env_path.exists():
        return
    # Only set env vars that are not already defined.
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


# Load environment variables from local .env if present (never committed).
_load_env_file(PROJECT_ROOT / ".env")

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
BRONZE_DIR = DATA_DIR / "bronze"
SILVER_DIR = DATA_DIR / "silver"
SILVER_CLEAN_DIR = SILVER_DIR / "clean"
GOLD_DIR = DATA_DIR / "gold"
SILVER_REJECTS_DIR = SILVER_DIR / "rejects"
REFERENCE_DIR = DATA_DIR / "reference"

RAW_INPUT_FILENAME = os.getenv("RAW_INPUT_FILENAME", "jira_issues_raw.txt")
RAW_INPUT_PATH = PROJECT_ROOT / RAW_INPUT_FILENAME

HOLIDAY_API_URL = os.getenv("HOLIDAY_API_URL", "https://date.nager.at/api/v3/PublicHolidays")
HOLIDAY_COUNTRY_CODE = os.getenv("HOLIDAY_COUNTRY_CODE", "BR")
DEFAULT_HOLIDAY_YEAR = int(os.getenv("DEFAULT_HOLIDAY_YEAR", "2026"))

AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID", "")
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID", "")
AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET", "")
AZURE_ACCOUNT_URL = os.getenv("AZURE_ACCOUNT_URL", "")

AZURE_CONTAINER_NAME = os.getenv("AZURE_CONTAINER_NAME", "")
AZURE_BLOB_PREFIX = os.getenv("AZURE_BLOB_PREFIX", "")
