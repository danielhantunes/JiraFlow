"""Download or copy Jira raw data into the Raw layer."""

from __future__ import annotations

import shutil
from pathlib import Path

from src.utils.config import (
    AZURE_BLOB_NAME,
    AZURE_CONTAINER_NAME,
    AZURE_STORAGE_CONNECTION_STRING,
    RAW_DIR,
    RAW_INPUT_PATH,
)


def ensure_raw_dir() -> None:
    """Ensure the raw data directory exists."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)


def copy_local_raw_file(source_path: Path, destination_dir: Path) -> Path:
    """
    Copy the local raw Jira file into the Raw layer.

    This is a fallback for local development where the raw file exists locally.
    """
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination_path = destination_dir / source_path.name
    shutil.copy2(source_path, destination_path)
    return destination_path


def download_from_azure_blob(destination_dir: Path) -> Path:
    """
    Download raw file from Azure Blob Storage into Raw layer.

    TODO: Implement Azure SDK download using environment variables.
    """
    if not all([AZURE_STORAGE_CONNECTION_STRING, AZURE_CONTAINER_NAME, AZURE_BLOB_NAME]):
        raise ValueError("Azure credentials are not configured in environment variables.")

    # TODO: Use azure-storage-blob to download the blob to destination_dir.
    # Example (placeholder):
    #   from azure.storage.blob import BlobServiceClient
    #   service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    #   blob_client = service_client.get_blob_client(container=AZURE_CONTAINER_NAME, blob=AZURE_BLOB_NAME)
    #   destination_path = destination_dir / AZURE_BLOB_NAME
    #   with open(destination_path, "wb") as f:
    #       f.write(blob_client.download_blob().readall())

    raise NotImplementedError("Azure download not implemented yet.")


def ingest_raw_data() -> Path:
    """
    Ingest raw data into the Raw layer.

    Priority:
    1. Copy local raw file if available.
    2. Attempt Azure Blob download (if configured).
    """
    ensure_raw_dir()

    if RAW_INPUT_PATH.exists():
        return copy_local_raw_file(RAW_INPUT_PATH, RAW_DIR)

    return download_from_azure_blob(RAW_DIR)
