"""Silver layer: clean and filter Bronze data."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import pandas as pd

from src.utils.config import SILVER_CLEAN_DIR, SILVER_REJECTS_DIR


def read_bronze(bronze_path: Path) -> pd.DataFrame:
    """Read Bronze data from disk."""
    # Bronze is stored as Parquet for efficient reads.
    return pd.read_parquet(bronze_path)


def extract_and_rename_fields(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract nested fields and standardize column names.
    """
    # Normalize list-like objects coming from Parquet.
    def _normalize_items(items: object) -> list | None:
        if isinstance(items, list):
            return items
        if hasattr(items, "tolist"):
            try:
                return items.tolist()
            except Exception:
                return None
        return None

    def _first_item_value(series: pd.Series, key: str) -> pd.Series:
        # Extract a key from the first element of a list of dicts.
        def _extract(items: object) -> object:
            normalized = _normalize_items(items)
            if normalized and isinstance(normalized[0], dict):
                return normalized[0].get(key, pd.NA)
            return pd.NA

        return series.apply(_extract)

    selected = df.copy()

    # Normalize assignee structure into explicit columns.
    if "assignee" in selected.columns:
        selected["assignee_name"] = _first_item_value(selected["assignee"], "name")
        selected["assignee_id"] = _first_item_value(selected["assignee"], "id")
        selected["assignee_email"] = _first_item_value(selected["assignee"], "email")

    # Extract created/resolved timestamps from the nested array.
    if "timestamps" in selected.columns:
        selected["created_at"] = _first_item_value(selected["timestamps"], "created_at")
        selected["resolved_at"] = _first_item_value(selected["timestamps"], "resolved_at")

    columns_map = {
        "id": "issue_id",
        "issue_type": "issue_type",
        "status": "status",
        "priority": "priority",
        "assignee_name": "assignee_name",
        "assignee_id": "assignee_id",
        "assignee_email": "assignee_email",
        "created_at": "created_at",
        "resolved_at": "resolved_at",
    }

    if "id" in selected.columns:
        selected["issue_id"] = selected["id"].astype("string")

    # Legacy Jira API field fallbacks (if present).
    legacy_map = {
        "fields.issuetype.name": "issue_type",
        "fields.assignee.displayName": "assignee_name",
        "fields.priority.name": "priority",
        "fields.status.name": "status",
        "fields.created": "created_at",
        "fields.resolutiondate": "resolved_at",
    }
    for source_col, target_col in legacy_map.items():
        if target_col not in selected.columns and source_col in selected.columns:
            selected[target_col] = selected[source_col]

    for target_col in columns_map.values():
        if target_col not in selected.columns:
            selected[target_col] = pd.NA

    return selected[list(columns_map.values())]


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and standardize data types.

    TODO: Add additional cleaning rules (nulls, invalid types).
    """
    df = df.copy()
    # Parse timestamps and store as ISO 8601 strings for sorting and portability.
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
    df["resolved_at"] = pd.to_datetime(df["resolved_at"], errors="coerce", utc=True)
    df["status"] = df["status"].astype("string").str.strip().str.title()
    df["priority"] = df["priority"].astype("string").str.strip().str.title()
    if "assignee_name" in df.columns:
        df["assignee_name"] = df["assignee_name"].fillna("Unassigned")
    df["created_at"] = df["created_at"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    df["resolved_at"] = df["resolved_at"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return df


def split_quality_checks(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split rows into valid and rejected sets with a reject_reason column.
    """
    df = df.copy()
    missing_issue_id = df["issue_id"].isna()
    missing_created_at = df["created_at"].isna()
    duplicate_issue_id = df["issue_id"].duplicated(keep="first")

    # Tag rows with a single reject reason to keep rejects simple to review.
    reject_reason = pd.Series(pd.NA, index=df.index, dtype="string")
    reject_reason = reject_reason.mask(missing_issue_id, "missing_issue_id")
    reject_reason = reject_reason.mask(
        missing_created_at, "missing_created_at"
    ).mask(duplicate_issue_id, "duplicate_issue_id")

    rejects = df[reject_reason.notna()].copy()
    rejects["reject_reason"] = reject_reason[reject_reason.notna()]

    valid = df[reject_reason.isna()].copy()
    return valid, rejects


def filter_statuses(df: pd.DataFrame) -> pd.DataFrame:
    """
    Keep Open, Done, and Resolved statuses.

    Open issues are retained in Silver but excluded from SLA in Gold.
    """
    # Keep only statuses needed for downstream SLA processing.
    return df[df["status"].isin(["Open", "Done", "Resolved"])]


def write_silver(df: pd.DataFrame, output_path: Path) -> Path:
    """Write Silver data to disk."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)
    return output_path


def write_rejects(df: pd.DataFrame, output_filename: str = "silver_rejects.parquet") -> Path:
    """Write rejected rows to the Silver rejects folder."""
    # Persist rejects for auditing/debugging.
    SILVER_REJECTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = SILVER_REJECTS_DIR / output_filename
    df.to_parquet(output_path, index=False)
    return output_path


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


def profile_silver_file(
    silver_path: Path,
    categorical_columns: Sequence[str] | None = None,
    top_n: int = 5,
) -> Dict[str, object]:
    """
    Load Silver Parquet and return profiling metrics.
    """
    df = pd.read_parquet(silver_path)
    default_categoricals = [
        "issue_type",
        "status",
        "priority",
        "assignee_name",
        "assignee_id",
        "assignee_email",
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


def run_silver(bronze_path: Path, output_filename: str = "silver_issues.parquet") -> Path:
    """Execute the Silver pipeline."""
    bronze_df = read_bronze(bronze_path)
    extracted = extract_and_rename_fields(bronze_df)
    cleaned = clean_data(extracted)
    validated, rejects = split_quality_checks(cleaned)
    if not rejects.empty:
        write_rejects(rejects)
    filtered = filter_statuses(validated)
    output_path = SILVER_CLEAN_DIR / output_filename
    return write_silver(filtered, output_path)
