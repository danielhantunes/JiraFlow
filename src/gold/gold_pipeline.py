"""Gold layer: compute SLA metrics for resolved issues."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Sequence, Set

import pandas as pd

from src.sla.sla_calculation import (
    calculate_business_hours,
    get_expected_sla_hours,
    get_sla_status,
)
from src.utils.config import (
    DEFAULT_HOLIDAY_YEAR,
    GOLD_DIR,
    HOLIDAY_COUNTRY_CODE,
    SILVER_CLEAN_DIR,
)
from src.utils.date_utils import fetch_public_holidays


def read_silver(silver_path: Path) -> pd.DataFrame:
    """Read Silver data from disk."""
    df = pd.read_parquet(silver_path)
    # Convert ISO strings back to timezone-aware datetimes for calculations.
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
    df["resolved_at"] = pd.to_datetime(df["resolved_at"], errors="coerce", utc=True)
    return df


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

    # Holiday lookup is used to exclude non-business days from SLA time.
    created_years = (
        pd.to_datetime(df["created_at"], errors="coerce", utc=True).dt.year.dropna().unique()
    )
    resolved_years = (
        pd.to_datetime(df["resolved_at"], errors="coerce", utc=True).dt.year.dropna().unique()
    )
    years = set(created_years) | set(resolved_years)
    if not years:
        years = {DEFAULT_HOLIDAY_YEAR}
    holidays = build_holiday_set(years)

    # Compute business-hour resolution time per issue.
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
    drop_cols = [col for col in ["assignee_id", "assignee_email"] if col in df.columns]
    return df.drop(columns=drop_cols)


def write_gold(df: pd.DataFrame, output_path: Path) -> Path:
    """Write Gold data to disk."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)
    return output_path


def build_sla_reports(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """Build aggregated SLA reports from Gold data."""
    required_cols = {"issue_id", "issue_type", "assignee_name", "resolution_time_business_hours"}
    missing = required_cols - set(df.columns)
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ValueError(f"Gold data is missing required columns: {missing_list}")

    by_assignee = (
        df.groupby("assignee_name", dropna=False)
        .agg(
            issue_count=("issue_id", "count"),
            sla_avg_hours=("resolution_time_business_hours", "mean"),
        )
        .reset_index()
    )
    by_assignee["sla_avg_hours"] = by_assignee["sla_avg_hours"].round(2)

    by_issue_type = (
        df.groupby("issue_type", dropna=False)
        .agg(
            issue_count=("issue_id", "count"),
            sla_avg_hours=("resolution_time_business_hours", "mean"),
        )
        .reset_index()
    )
    by_issue_type["sla_avg_hours"] = by_issue_type["sla_avg_hours"].round(2)

    return {
        "sla_avg_by_assignee.csv": by_assignee,
        "sla_avg_by_issue_type.csv": by_issue_type,
    }


def write_sla_reports(df: pd.DataFrame, output_dir: Path = GOLD_DIR / "reports") -> Dict[str, Path]:
    """Write aggregated SLA reports to disk."""
    output_dir.mkdir(parents=True, exist_ok=True)
    reports = build_sla_reports(df)
    output_paths: Dict[str, Path] = {}
    for filename, report_df in reports.items():
        output_path = output_dir / filename
        report_df.to_csv(output_path, index=False)
        output_paths[filename] = output_path
    return output_paths


def profile_dataframe(
    df: pd.DataFrame,
    categorical_columns: Sequence[str] | None = None,
    top_n: int = 5,
) -> Dict[str, object]:
    """
    Generate lightweight profiling metrics for a dataframe.

    Returns:
        dict with row count, null percentage per column, cardinality per column,
        and top values for categorical columns.
    """
    categorical_columns = list(categorical_columns or [])
    null_pct = (df.isna().mean() * 100).round(2).to_dict()
    cardinality = df.nunique(dropna=True).to_dict()

    top_values: Dict[str, Dict[str, int]] = {}
    for col in categorical_columns:
        if col in df.columns:
            counts = df[col].astype("string").value_counts(dropna=True).head(top_n)
            top_values[col] = counts.to_dict()

    return {
        "row_count": int(len(df)),
        "null_pct": null_pct,
        "cardinality": cardinality,
        "top_values": top_values,
    }


def profile_gold_file(
    gold_path: Path,
    categorical_columns: Sequence[str] | None = None,
    top_n: int = 5,
) -> Dict[str, object]:
    """
    Load Gold Parquet and return profiling metrics.
    """
    df = pd.read_parquet(gold_path)
    default_categoricals = [
        "issue_type",
        "status",
        "priority",
        "assignee_name",
        "sla_status",
    ]
    return profile_dataframe(
        df,
        categorical_columns=categorical_columns or default_categoricals,
        top_n=top_n,
    )


def format_profile_output(profile: Dict[str, object]) -> str:
    """Format profiling metrics into a readable string."""
    row_count = profile.get("row_count", 0)
    null_pct = profile.get("null_pct", {})
    cardinality = profile.get("cardinality", {})
    top_values = profile.get("top_values", {})

    sections: List[str] = []
    sections.append(f"Row count: {row_count}")

    if null_pct:
        sections.append("Null % by column:")
        for col, pct in sorted(null_pct.items()):
            sections.append(f"  - {col}: {pct}%")

    if cardinality:
        sections.append("Cardinality by column:")
        for col, count in sorted(cardinality.items()):
            sections.append(f"  - {col}: {count}")

    if top_values:
        sections.append("Top values (categorical):")
        for col, values in sorted(top_values.items()):
            sections.append(f"  - {col}:")
            for value, count in values.items():
                sections.append(f"      {value}: {count}")

    return "\n".join(sections)


def preview_dataframe(df: pd.DataFrame, n: int = 10) -> str:
    """Return a readable preview of the first N rows."""
    preview = df.head(n)
    text = preview.to_string(index=False)
    lines = text.splitlines()
    if len(lines) > 1:
        lines.insert(1, "-" * len(lines[0]))
    return "\n".join(lines)


def run_gold(
    silver_path: Path = SILVER_CLEAN_DIR / "jira_silver.parquet",
    output_filename: str = "jira_gold.parquet",
) -> Path:
    """Execute the Gold pipeline."""
    silver_df = read_silver(silver_path)
    resolved = filter_resolved(silver_df)
    with_sla = calculate_sla_metrics(resolved)
    final_df = select_gold_columns(with_sla)
    output_path = GOLD_DIR / output_filename
    write_gold(final_df, output_path)
    write_sla_reports(final_df)
    return output_path
