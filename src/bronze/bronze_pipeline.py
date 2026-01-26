"""Bronze layer: normalize and flatten raw Jira JSON."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Union

import pandas as pd
import json

from src.utils.config import BRONZE_DIR


def read_raw_json(raw_file_path: Path) -> Dict:
    """Read the raw JSON file from disk."""
    # TODO: Handle large files with streaming if needed.
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
    return pd.json_normalize(issues)


def select_and_rename_fields(df: pd.DataFrame) -> pd.DataFrame:
    """
    Select and rename relevant fields for Bronze.

    TODO: Update field mappings based on the actual Jira payload.
    """
    columns_map = {
        "id": "issue_id",
        "fields.issuetype.name": "issue_type",
        "fields.assignee.displayName": "assignee",
        "fields.priority.name": "priority",
        "fields.status.name": "status",
        "fields.created": "created_at",
        "fields.resolutiondate": "resolved_at",
    }
    selected = df.rename(columns=columns_map)
    for source_col, target_col in columns_map.items():
        if target_col not in selected.columns:
            selected[target_col] = pd.NA
    return selected[list(columns_map.values())]


def add_source_file(df: pd.DataFrame, source_file: Path) -> pd.DataFrame:
    """Add a source file column for lineage."""
    df = df.copy()
    df["source_file"] = source_file.name
    return df


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
    output_filename: str = "jira_bronze.parquet",
) -> Path:
    """Execute the Bronze pipeline."""
    raw_paths = _coerce_raw_paths(raw_file_path)
    frames: List[pd.DataFrame] = []
    for path in raw_paths:
        raw_json = read_raw_json(path)
        normalized = normalize_issues(raw_json)
        bronze_df = select_and_rename_fields(normalized)
        bronze_df = add_source_file(bronze_df, path)
        frames.append(bronze_df)
    bronze_df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    output_path = BRONZE_DIR / output_filename
    return write_bronze(bronze_df, output_path)
