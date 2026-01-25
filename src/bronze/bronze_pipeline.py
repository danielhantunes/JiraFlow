"""Bronze layer: normalize and flatten raw Jira JSON."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import pandas as pd
import json

from src.utils.config import BRONZE_DIR


def read_raw_json(raw_file_path: Path) -> Dict:
    """Read the raw JSON file from disk."""
    # TODO: Handle large files with streaming if needed.
    with raw_file_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def normalize_issues(raw_json: Dict) -> pd.DataFrame:
    """
    Normalize nested Jira JSON into a flat table.

    TODO: Validate schema and adjust fields for the actual file structure.
    """
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
    existing = [col for col in columns_map if col in df.columns]
    selected = df[existing].rename(columns=columns_map)
    return selected


def write_bronze(df: pd.DataFrame, output_path: Path) -> Path:
    """Write Bronze data to disk."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return output_path


def run_bronze(raw_file_path: Path, output_filename: str = "jira_bronze.csv") -> Path:
    """Execute the Bronze pipeline."""
    raw_json = read_raw_json(raw_file_path)
    normalized = normalize_issues(raw_json)
    bronze_df = select_and_rename_fields(normalized)
    output_path = BRONZE_DIR / output_filename
    return write_bronze(bronze_df, output_path)
