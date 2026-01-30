"""Bronze layer: normalize and flatten raw Jira JSON."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Union

import pandas as pd
import json

from src.utils.config import BRONZE_DIR


def read_raw_json(raw_file_path: Path) -> Dict:
    """Read the raw JSON file from disk."""
    # Read the entire JSON payload into memory.
    with raw_file_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def validate_raw_schema(raw_json: Dict) -> None:
    """Validate minimal raw JSON structure."""
    if "issues" not in raw_json:
        raise ValueError("Raw JSON is missing required 'issues' field.")
    if not isinstance(raw_json["issues"], list):
        raise ValueError("Raw JSON 'issues' field must be a list.")


def normalize_issues(raw_json: Dict) -> pd.DataFrame:
    """
    Normalize nested Jira JSON into a flat table.

    TODO: Validate schema and adjust fields for the actual file structure.
    """
    validate_raw_schema(raw_json)
    issues = raw_json.get("issues", [])
    # Minimal normalization: flatten nested JSON into a tabular structure.
    return pd.json_normalize(issues)


def add_source_file(df: pd.DataFrame, source_file: Path) -> pd.DataFrame:
    """Add a source file column for lineage."""
    df = df.copy()
    # Keep filename for traceability across layers.
    df["source_file"] = source_file.name
    return df


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
    # Optional profiling for quick data-quality checks.
    categorical_columns = list(categorical_columns or [])
    def _safe_value(value: object) -> object:
        if isinstance(value, (list, dict)):
            return json.dumps(value, sort_keys=True, ensure_ascii=False)
        if hasattr(value, "tolist") and not isinstance(value, (str, bytes)):
            try:
                return json.dumps(value.tolist(), sort_keys=True, ensure_ascii=False)
            except TypeError:
                return str(value)
        return value

    null_pct = (df.isna().mean() * 100).round(2).to_dict()
    cardinality = {
        col: df[col].map(_safe_value).nunique(dropna=True) for col in df.columns
    }

    top_values: Dict[str, Dict[str, int]] = {}
    for col in categorical_columns:
        if col in df.columns:
            counts = (
                df[col]
                .map(_safe_value)
                .astype("string")
                .value_counts(dropna=True)
                .head(top_n)
            )
            top_values[col] = counts.to_dict()

    return {
        "row_count": int(len(df)),
        "null_pct": null_pct,
        "cardinality": cardinality,
        "top_values": top_values,
    }


def basic_quality_checks(df: pd.DataFrame) -> Dict[str, int]:
    """
    Basic quality checks for Bronze data.

    Returns counts of missing required fields and duplicates.
    """
    # Basic counts used for manual inspection.
    missing_issue_id = int(df["issue_id"].isna().sum()) if "issue_id" in df.columns else 0
    missing_created_at = (
        int(df["created_at"].isna().sum()) if "created_at" in df.columns else 0
    )
    duplicate_issue_id = (
        int(df["issue_id"].duplicated().sum()) if "issue_id" in df.columns else 0
    )

    return {
        "missing_issue_id": missing_issue_id,
        "missing_created_at": missing_created_at,
        "duplicate_issue_id": duplicate_issue_id,
    }


def profile_bronze_file(
    bronze_path: Path,
    categorical_columns: Sequence[str] | None = None,
    top_n: int = 5,
) -> Dict[str, object]:
    """
    Load Bronze parquet and return profiling metrics.
    """
    df = pd.read_parquet(bronze_path)
    return profile_dataframe(df, categorical_columns=categorical_columns, top_n=top_n)


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


def write_bronze(df: pd.DataFrame, output_path: Path) -> Path:
    """Write Bronze data to disk."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)
    return output_path


RawPathInput = Union[Path, str, Sequence[Path], Sequence[str]]


def _coerce_raw_paths(raw_file_path: RawPathInput) -> List[Path]:
    if isinstance(raw_file_path, (Path, str)):
        return [Path(raw_file_path)]
    return [Path(p) for p in raw_file_path]


def run_bronze(
    raw_file_path: RawPathInput,
    output_filename: str = "bronze_issues.parquet",
) -> Path:
    """Execute the Bronze pipeline."""
    raw_paths = _coerce_raw_paths(raw_file_path)
    frames: List[pd.DataFrame] = []
    for path in raw_paths:
        raw_json = read_raw_json(path)
        normalized = normalize_issues(raw_json)
        normalized = add_source_file(normalized, path)
        frames.append(normalized)
    bronze_df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    output_path = BRONZE_DIR / output_filename
    return write_bronze(bronze_df, output_path)
