# 🚧 Jira Medallion Pipeline  
*This project is under active development.*

## Overview
This project implements a **local data engineering pipeline** that ingests a nested JSON file of Jira issues and processes it through a **Medallion architecture (Raw → Bronze → Silver → Gold)** to produce reliable SLA metrics.

The goal is to demonstrate **data modeling, data quality practices, and pipeline structuring** aligned with real-world analytics and reporting use cases.

---

## Project Purpose
- Ingest Jira issue data from a JSON source
- Normalize and clean semi-structured data
- Apply business rules for SLA calculation
- Produce analytics-ready datasets using layered data design

---

## Architecture — Medallion Layers

| Layer  | Responsibility |
|------|---------------|
| **Raw** | Store the original input file exactly as received |
| **Bronze** | Normalize/flatten raw JSON with minimal transformation (Parquet output) |
| **Silver** | Extract nested fields, standardize columns, clean data, and filter statuses (Parquet output) |
| **Gold** | Keep only Done / Resolved issues and compute SLA metrics |

Note: Raw JSON is first normalized (flattened) into a tabular structure, then specific fields are extracted and renamed in Silver.

```
Raw  →  Bronze  →  Silver  →  Gold
 |        |         |         |
data/raw data/bronze data/silver data/gold
```

---

## Project Structure

```
project_root/
├── data/
│   ├── raw/
│   ├── bronze/
│   ├── silver/
│   │   ├── clean/
│   │   └── rejects/
│   ├── reference/
│   └── gold/
├── src/
│   ├── ingestion/   # Raw data ingestion
│   ├── bronze/      # Minimal normalization (raw-like)
│   ├── silver/      # Extraction, cleaning, filtering
│   ├── gold/        # SLA calculations and analytics output
│   ├── sla/         # Reusable SLA utilities
│   └── utils/       # Configuration and date helpers
├── .env
├── .env.example
├── README.md
├── requirements.txt
└── .gitignore
```

---

## How to Run

### Install dependencies
```bash
pip install -r requirements.txt
```

---

### Provide input data (optional)
Option A — place the Jira export file in the project root:

```text
jira_issues_raw.json
```

Option B — skip local file and use Azure Blob ingestion via environment variables.

---

### Run the full pipeline
```bash
python -m src.main
```

Each layer can also be executed independently via its corresponding module.

### Output files
- `data/raw/jira_issues_raw.json`
- `data/bronze/jira_bronze.parquet`
- `data/silver/clean/jira_silver.parquet`
- `data/silver/rejects/jira_silver_rejects.parquet`
- `data/gold/jira_gold.parquet`
- `data/gold/reports/sla_avg_by_assignee.csv`
- `data/gold/reports/sla_avg_by_issue_type.csv`

Parquet is used as the canonical format because it is columnar, compact, and faster for analytics workloads.
CSV export is optional for analyst convenience.

Optional CSV export:
```bash
python -c "import pandas as pd; df = pd.read_parquet('data/gold/jira_gold.parquet'); df.to_csv('data/gold/jira_gold.csv', index=False)"
```

---

## Dependencies
- pandas
- pyarrow (required for Parquet output)
- azure-identity (for Azure Blob Storage authentication)

---

## Environment Variables

### Required (Azure service principal)
- AZURE_TENANT_ID
- AZURE_CLIENT_ID
- AZURE_CLIENT_SECRET
- AZURE_ACCOUNT_URL
- AZURE_CONTAINER_NAME

### Optional
- RAW_INPUT_FILENAME (default: jira_issues_raw.json)
- AZURE_BLOB_PREFIX (downloads all blobs if empty)
- HOLIDAY_API_URL (default: https://date.nager.at/api/v3/PublicHolidays)
- HOLIDAY_COUNTRY_CODE (default: BR)
- DEFAULT_HOLIDAY_YEAR (default: 2026)

---

## ⚙️ Local Setup
Copy the example environment file and fill in your values:

```bash
cp .env.example .env
```

Environment variables are loaded locally using a lightweight `.env` parser (stdlib).

---

## 🔍 Optional: Bronze Data Profiling

The Bronze layer includes **lightweight data profiling utilities** to perform a quick quality check before moving data to Silver.

Note: Bronze is minimally transformed and may include nested fields. Silver profiling is more stable for column-level checks.

### Metrics
- Percentage of null values per column
- Column cardinality
- Top values for key categorical fields

### Run
```bash
python -c "from pathlib import Path; from src.bronze.bronze_pipeline import profile_bronze_file, format_profile_output; profile = profile_bronze_file(Path('data/bronze/jira_bronze.parquet'), categorical_columns=['issue_type','status','priority']); print(format_profile_output(profile))"
```

### Example output
```
Row count: 12453
Null % by column:
  - assignee: 12.4%
Cardinality by column:
  - issue_type: 7
Top values (categorical):
  - status:
      Done: 5321
      In Progress: 4182
```

You can also preview a small sample for a quick visual check:
```bash
python -c "import pandas as pd; from src.bronze.bronze_pipeline import preview_dataframe; df = pd.read_parquet('data/bronze/jira_bronze.parquet'); print(preview_dataframe(df, n=10))"
```

This step is optional but recommended as a **quality gate between Bronze and Silver**.

---

## 🔍 Optional: Silver Data Profiling

The Silver layer includes optional profiling utilities to validate cleaned data before Gold.

### Run
```bash
python -c "from pathlib import Path; from src.silver.silver_pipeline import profile_silver_file, format_profile_output; profile = profile_silver_file(Path('data/silver/clean/jira_silver.parquet'), categorical_columns=['issue_type','status','priority','assignee_name','assignee_id','assignee_email']); print(format_profile_output(profile))"
```

### Preview
```bash
python -c "import pandas as pd; from src.silver.silver_pipeline import preview_dataframe; df = pd.read_parquet('data/silver/clean/jira_silver.parquet'); print(preview_dataframe(df, n=10))"
```

This step is optional but recommended as a **quality gate between Silver and Gold**.

---

## 🔍 Optional: Gold Data Profiling

The Gold layer includes optional profiling utilities to validate the final SLA table.

### Run
```bash
python -c "from pathlib import Path; from src.gold.gold_pipeline import profile_gold_file, format_profile_output; profile = profile_gold_file(Path('data/gold/jira_gold.parquet')); print(format_profile_output(profile))"
```

### Preview
```bash
python -c "import pandas as pd; from src.gold.gold_pipeline import preview_dataframe; df = pd.read_parquet('data/gold/jira_gold.parquet'); print(preview_dataframe(df, n=10))"
```

This step is optional and helps validate the final Gold output.

---

## ✅ Silver Quality Checks and Rejects

During Silver processing, basic quality checks are applied:
- Rows missing `issue_id` or `created_at` are rejected
- Duplicate `issue_id` rows are rejected

Rejected rows are saved to:
`data/silver/rejects/jira_silver_rejects.parquet`

This keeps the Silver dataset clean while preserving discarded records for auditing.

---

## SLA Calculation Logic
- SLA is calculated as **resolution time in business hours**
- Business hours exclude weekends and national holidays
- Each business day counts **24 hours**
- Holiday years are derived from the data (`created_at` and `resolved_at`)
- Holiday data is cached locally under `data/reference/` to avoid repeated API calls
- Open issues are excluded from SLA metrics
- SLA is considered **met** when:

```
actual_hours ≤ expected_hours
```

### Expected SLA by Priority
| Priority | Expected SLA |
|----------|--------------|
| High     | 24 hours     |
| Medium   | 72 hours     |
| Low      | 120 hours    |

---

## Suggested KPIs (Gold)
- SLA compliance rate (% met vs violated)
- Average resolution time (business hours)
- SLA compliance by priority
- Average resolution time by priority
- Resolution time by assignee
- Volume of resolved issues per priority

---

## Final Gold Schema
- issue_id
- issue_type
- assignee_name
- priority
- created_at
- resolved_at
- resolution_time_business_hours
- expected_sla_hours
- sla_status

Note: `assignee_id` and `assignee_email` are excluded from Gold to keep the
analytics table focused on reporting fields.

---

## Data Dictionary

### Gold SLA Table (`data/gold/jira_gold.parquet`)
| Column | Description |
|--------|-------------|
| issue_id | Unique Jira issue identifier |
| issue_type | Type/category of issue (e.g., Bug, Task) |
| assignee_name | Analyst responsible for the issue |
| priority | Issue priority (High, Medium, Low) |
| created_at | Issue creation timestamp (UTC, ISO 8601) |
| resolved_at | Issue resolution timestamp (UTC, ISO 8601) |
| resolution_time_business_hours | Resolution time in business hours |
| expected_sla_hours | Target SLA hours based on priority |
| sla_status | SLA outcome: met or violated |

### Report: SLA Médio por Analista (`data/gold/reports/sla_avg_by_assignee.csv`)
| Column | Description |
|--------|-------------|
| assignee_name | Analyst responsible for the issues |
| issue_count | Number of resolved issues for the analyst |
| sla_avg_hours | Average SLA (business hours) for the analyst |

### Report: SLA Médio por Tipo de Chamado (`data/gold/reports/sla_avg_by_issue_type.csv`)
| Column | Description |
|--------|-------------|
| issue_type | Type/category of issue |
| issue_count | Number of resolved issues for the type |
| sla_avg_hours | Average SLA (business hours) for the type |

---

## Notes
- Each Medallion layer can run independently
- Azure Blob ingestion supports downloading all blobs in a container
- The project is designed for local execution
