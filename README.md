🚧 This project is under active development.

# Jira Medallion Pipeline

## Project purpose
Build a local data pipeline that ingests a nested JSON file of Jira issues and
processes it through Raw, Bronze, Silver, and Gold layers to compute SLA metrics.

## Architecture (Medallion layers)
- **Raw**: store the original file as-is
- **Bronze**: normalize and flatten JSON, select/rename key fields (Parquet output)
- **Silver**: clean data, convert dates, keep Open/Done/Resolved
- **Gold**: keep only Done/Resolved, compute SLA metrics

```
Raw  ->  Bronze  ->  Silver  ->  Gold
   |        |         |         |
 data/raw  data/bronze data/silver data/gold
```

## Project structure
- `src/`: application code and pipeline logic
- `src/ingestion/`: raw ingestion into `data/raw`
- `src/bronze/`: normalization and field selection
- `src/silver/`: cleaning and filtering
- `src/gold/`: SLA calculations and analytical output
- `src/sla/`: reusable SLA utilities
- `src/utils/`: config and date helpers
- `data/raw`, `data/bronze`, `data/silver`, `data/gold`: local layer outputs

```
project_root/
├── data/
│   ├── raw/
│   ├── bronze/
│   ├── silver/
│   └── gold/
├── src/
│   ├── ingestion/
│   ├── bronze/
│   ├── silver/
│   ├── gold/
│   ├── sla/
│   └── utils/
├── .env
├── .env.example
├── README.md
├── requirements.txt
└── .gitignore
```

## How to run
1. Create a virtual environment and install dependencies:
   - `pip install -r requirements.txt`
2. Place `jira_issues_raw.txt` in the project root (or set `RAW_INPUT_FILENAME`).
3. Run the pipeline:
   - `python -m src.main`

Dependencies:
- `pandas`
- `azure-identity`
- `pyarrow` (required for Parquet output)

Environment variables (service principal):
- `RAW_INPUT_FILENAME` (default: `jira_issues_raw.txt`)
- `HOLIDAY_API_URL` (default: `https://date.nager.at/api/v3/PublicHolidays`)
- `HOLIDAY_COUNTRY_CODE` (default: `US`)
- `AZURE_TENANT_ID`
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`
- `AZURE_ACCOUNT_URL`
- `AZURE_CONTAINER_NAME`
- `AZURE_BLOB_PREFIX` (optional, downloads all blobs if empty)

Local setup:
- Copy `.env.example` to `.env` and fill in the values locally.

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
- Azure Blob download uses service principal auth and supports downloading all blobs in a container.
