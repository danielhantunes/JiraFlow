"""Main orchestration for Jira Medallion pipeline."""

from __future__ import annotations

from src.bronze.bronze_pipeline import run_bronze
from src.gold.gold_pipeline import run_gold
from src.ingestion.ingest_jira_raw import ingest_raw_data
from src.silver.silver_pipeline import run_silver


def run_pipeline() -> None:
    """Run the end-to-end pipeline."""
    # Orchestrate all layers in order.
    raw_path = ingest_raw_data()
    bronze_path = run_bronze(raw_path)
    run_silver(bronze_path)
run_gold()


if __name__ == "__main__":
    run_pipeline()
