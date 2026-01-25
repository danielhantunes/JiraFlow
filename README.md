# Jira Medallion Pipeline

## Project purpose
Build a local data pipeline that ingests a nested JSON file of Jira issues and
processes it through Raw, Bronze, Silver, and Gold layers to compute SLA metrics.

## Architecture (Medallion layers)
- **Raw**: store the original file as-is
- **Bronze**: normalize and flatten JSON, select/rename key fields
- **Silver**: clean data, convert dates, keep Open/Done/Resolved
- **Gold**: keep only Done/Resolved, compute SLA metrics

## How to run
1. Create a virtual environment and install dependencies:
   - `pip install -r requirements.txt`
2. Place `jira_issues_raw.txt` in the project root (or set `RAW_INPUT_FILENAME`).
3. Run the pipeline:
   - `python -m src.main`

Environment variables:
- `RAW_INPUT_FILENAME` (default: `jira_issues_raw.txt`)
- `HOLIDAY_API_URL` (default: `https://date.nager.at/api/v3/PublicHolidays`)
- `HOLIDAY_COUNTRY_CODE` (default: `US`)
- `AZURE_STORAGE_CONNECTION_STRING`
- `AZURE_CONTAINER_NAME`
- `AZURE_BLOB_NAME`

## SLA calculation logic
- SLA = resolution time in business hours
- Business hours exclude weekends and national holidays
- Open issues are excluded from SLA calculations
- SLA status is **met** when actual hours <= expected hours

## Final Gold schema
- `issue_id`
- `issue_type`
- `assignee`
- `priority`
- `created_at`
- `resolved_at`
- `resolution_time_business_hours`
- `expected_sla_hours`
- `sla_status`

## Notes
- Each layer can run independently through its respective module.
- Azure Blob download is a placeholder and must be implemented to use cloud ingestion.
