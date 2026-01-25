"""Download or copy Jira raw data into the Raw layer."""

from __future__ import annotations

import shutil
from pathlib import Path

from src.utils.config import (
    AZURE_ACCOUNT_URL,
    AZURE_BLOB_PREFIX,
    AZURE_CLIENT_ID,
    AZURE_CLIENT_SECRET,
    AZURE_CONTAINER_NAME,
    AZURE_TENANT_ID,
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


def download_from_azure_blob(destination_dir: Path) -> list[Path]:
    """
    Download raw files from Azure Blob Storage into Raw layer.

    Downloads all blobs in the container or filters by prefix if provided.
    Returns the list of downloaded file paths.
    """
    has_service_principal = all(
        [AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_ACCOUNT_URL]
    )
    if not has_service_principal:
        raise ValueError(
            "Azure credentials are not configured in environment variables."
        )
    if not AZURE_CONTAINER_NAME:
        raise ValueError("Azure container name is not configured.")

    from azure.identity import ClientSecretCredential
    from azure.storage.blob import BlobServiceClient

    credential = ClientSecretCredential(
        AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET
    )
    service_client = BlobServiceClient(
        account_url=AZURE_ACCOUNT_URL,
        credential=credential,
    )
    container_client = service_client.get_container_client(AZURE_CONTAINER_NAME)

    destination_dir.mkdir(parents=True, exist_ok=True)
    blob_names = [
        blob.name
        for blob in container_client.list_blobs(name_starts_with=AZURE_BLOB_PREFIX or None)
    ]
    if not blob_names:
        raise FileNotFoundError("No blobs found for the provided container/prefix.")

    downloaded_paths: list[Path] = []
    for blob_name in blob_names:
        blob_client = container_client.get_blob_client(blob=blob_name)
        destination_path = destination_dir / Path(blob_name).name
        with open(destination_path, "wb") as file_handle:
            file_handle.write(blob_client.download_blob().readall())
        downloaded_paths.append(destination_path)

    return downloaded_paths


def ingest_raw_data() -> Path | list[Path]:
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
