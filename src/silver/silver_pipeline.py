"""Silver layer: clean and filter Bronze data."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.utils.config import SILVER_DIR


def read_bronze(bronze_path: Path) -> pd.DataFrame:
    """Read Bronze data from disk."""
    return pd.read_parquet(bronze_path)


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and standardize data types.

    TODO: Add additional cleaning rules (nulls, invalid types).
    """
    df = df.copy()
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    df["resolved_at"] = pd.to_datetime(df["resolved_at"], errors="coerce")
    df["status"] = df["status"].astype("string").str.strip().str.title()
    df["priority"] = df["priority"].astype("string").str.strip().str.title()
    df["assignee"] = df["assignee"].fillna("Unassigned")
    return df


def apply_basic_quality_checks(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply simple quality checks:
    - drop rows missing issue_id or created_at
    - drop duplicate issue_id
    """
    df = df.copy()
    df = df.dropna(subset=["issue_id", "created_at"])
    df = df.drop_duplicates(subset=["issue_id"])
    return df


def filter_statuses(df: pd.DataFrame) -> pd.DataFrame:
    """
    Keep Open, Done, and Resolved statuses.

    Open issues are retained in Silver but excluded from SLA in Gold.
    """
    return df[df["status"].isin(["Open", "Done", "Resolved"])]


def write_silver(df: pd.DataFrame, output_path: Path) -> Path:
    """Write Silver data to disk."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return output_path


def run_silver(bronze_path: Path, output_filename: str = "jira_silver.csv") -> Path:
    """Execute the Silver pipeline."""
    bronze_df = read_bronze(bronze_path)
    cleaned = clean_data(bronze_df)
    validated = apply_basic_quality_checks(cleaned)
    filtered = filter_statuses(validated)
    output_path = SILVER_DIR / output_filename
    return write_silver(filtered, output_path)
