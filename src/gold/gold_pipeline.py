"""Gold layer: compute SLA metrics for resolved issues."""

from __future__ import annotations

from pathlib import Path
from typing import Set

import pandas as pd

from src.sla.sla_calculation import (
    calculate_business_hours,
    get_expected_sla_hours,
    get_sla_status,
)
from src.utils.config import GOLD_DIR, HOLIDAY_COUNTRY_CODE
from src.utils.date_utils import fetch_public_holidays


def read_silver(silver_path: Path) -> pd.DataFrame:
    """Read Silver data from disk."""
    return pd.read_csv(silver_path, parse_dates=["created_at", "resolved_at"])


def filter_resolved(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only Done and Resolved issues."""
    return df[df["status"].isin(["Done", "Resolved"])]


def build_holiday_set(years: Set[int]) -> Set:
    """Fetch holidays for all relevant years."""
    holidays = set()
    for year in years:
        holidays |= fetch_public_holidays(year, country_code=HOLIDAY_COUNTRY_CODE)
    return holidays


def calculate_sla_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate SLA metrics for resolved issues."""
    df = df.copy()

    years = set(df["created_at"].dt.year.unique()) | set(df["resolved_at"].dt.year.unique())
    holidays = build_holiday_set(years)

    df["resolution_time_business_hours"] = df.apply(
        lambda row: calculate_business_hours(
            row["created_at"], row["resolved_at"], holidays
        ),
        axis=1,
    )
    df["expected_sla_hours"] = df["priority"].apply(get_expected_sla_hours)
    df["sla_status"] = df.apply(
        lambda row: get_sla_status(
            row["resolution_time_business_hours"], row["expected_sla_hours"]
        ),
        axis=1,
    )

    return df


def select_gold_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Select final Gold columns for analytics."""
    return df[
        [
            "issue_id",
            "issue_type",
            "assignee",
            "priority",
            "created_at",
            "resolved_at",
            "resolution_time_business_hours",
            "expected_sla_hours",
            "sla_status",
        ]
    ]


def write_gold(df: pd.DataFrame, output_path: Path) -> Path:
    """Write Gold data to disk."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return output_path


def run_gold(silver_path: Path, output_filename: str = "jira_gold.csv") -> Path:
    """Execute the Gold pipeline."""
    silver_df = read_silver(silver_path)
    resolved = filter_resolved(silver_df)
    with_sla = calculate_sla_metrics(resolved)
    final_df = select_gold_columns(with_sla)
    output_path = GOLD_DIR / output_filename
    return write_gold(final_df, output_path)
