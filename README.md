# Jira Medallion Pipeline

## Overview
This project implements a **local data engineering pipeline** that ingests a nested JSON file of Jira issues and processes it through a **Medallion architecture (Raw → Bronze → Silver → Gold)** to produce reliable SLA metrics and aggregated reports.

### Quick start
```bash
pip install -r requirements.txt
python -m src.main
```

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

## Requirement Coverage
- **Medallion layers** implemented with local persistence for each stage
- **Azure Blob ingestion** via Service Principal (read-only)
- **Nested JSON handling** with normalization and field extraction
- **SLA rules** (business days, weekends/holidays, priority mapping)
- **Gold reports** for SLA average by analyst and by issue type
- **Data quality** with Silver rejects output

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
│       └── reports/
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

### (Optional) Create a virtual environment
```bash
python -m venv .venv
```

Activate it:
```bash
# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate
```

---

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
- `data/raw/<original_source_name>.json`
- `data/bronze/bronze_issues.parquet`
- `data/silver/clean/silver_issues.parquet`
- `data/silver/rejects/silver_rejects.parquet`
- `data/gold/gold_sla_issues.parquet`
- `data/gold/reports/gold_sla_by_analyst.csv`
- `data/gold/reports/gold_sla_by_issue_type.csv`

Parquet is used as the canonical format because it is columnar, compact, and faster for analytics workloads.
CSV export is optional for analyst convenience.

Optional CSV export:
```bash
python -c "import pandas as pd; df = pd.read_parquet('data/gold/gold_sla_issues.parquet'); df.to_csv('data/gold/gold_sla_issues.csv', index=False)"
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
python -c "from pathlib import Path; from src.bronze.bronze_pipeline import profile_bronze_file, format_profile_output; profile = profile_bronze_file(Path('data/bronze/bronze_issues.parquet'), categorical_columns=['issue_type','status','priority']); print(format_profile_output(profile))"
```

You can also preview a small sample for a quick visual check:
```bash
python -c "import pandas as pd; from src.bronze.bronze_pipeline import preview_dataframe; df = pd.read_parquet('data/bronze/bronze_issues.parquet'); print(preview_dataframe(df, n=10))"
```

This step is optional but recommended as a **quality gate between Bronze and Silver**.

---

## 🔍 Optional: Silver Data Profiling

The Silver layer includes optional profiling utilities to validate cleaned data before Gold.

### Run
```bash
python -c "from pathlib import Path; from src.silver.silver_pipeline import profile_silver_file, format_profile_output; profile = profile_silver_file(Path('data/silver/clean/silver_issues.parquet'), categorical_columns=['issue_type','status','priority','assignee_name','assignee_id','assignee_email']); print(format_profile_output(profile))"
```

### Preview
```bash
python -c "import pandas as pd; from src.silver.silver_pipeline import preview_dataframe; df = pd.read_parquet('data/silver/clean/silver_issues.parquet'); print(preview_dataframe(df, n=10))"
```

This step is optional but recommended as a **quality gate between Silver and Gold**.

---

## 🔍 Optional: Gold Data Profiling

The Gold layer includes optional profiling utilities to validate the final SLA table.

### Run
```bash
python -c "from pathlib import Path; from src.gold.gold_pipeline import profile_gold_file, format_profile_output; profile = profile_gold_file(Path('data/gold/gold_sla_issues.parquet')); print(format_profile_output(profile))"
```

### Preview
```bash
python -c "import pandas as pd; from src.gold.gold_pipeline import preview_dataframe; df = pd.read_parquet('data/gold/gold_sla_issues.parquet'); print(preview_dataframe(df, n=10))"
```

This step is optional and helps validate the final Gold output.

---

## ✅ Silver Quality Checks and Rejects

During Silver processing, basic quality checks are applied:
- Rows missing `issue_id` or `created_at` are rejected
- Duplicate `issue_id` rows are rejected

Rejected rows are saved to:
`data/silver/rejects/silver_rejects.parquet`

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
- resolution_hours
- sla_expected_hours
- is_sla_met

Note: `assignee_id` and `assignee_email` are excluded from Gold to keep the
analytics table focused on reporting fields.

---

## Data Dictionary

### Gold SLA Table (`data/gold/gold_sla_issues.parquet`)
| Column | Description |
|--------|-------------|
| issue_id | Unique Jira issue identifier |
| issue_type | Type/category of issue (e.g., Bug, Task) |
| assignee_name | Analyst responsible for the issue |
| priority | Issue priority (High, Medium, Low) |
| created_at | Issue creation timestamp (UTC, ISO 8601) |
| resolved_at | Issue resolution timestamp (UTC, ISO 8601) |
| resolution_hours | Resolution time in business hours |
| sla_expected_hours | Target SLA hours based on priority |
| is_sla_met | SLA outcome indicator (true/false) |

### Report: Average SLA by Assignee (`data/gold/reports/gold_sla_by_analyst.csv`)
| Column | Description |
|--------|-------------|
| assignee_name | Analyst responsible for the issues |
| issue_count | Number of resolved issues for the analyst |
| sla_avg_hours | Average SLA (business hours) for the analyst |

### Report: Average SLA by Issue Type (`data/gold/reports/gold_sla_by_issue_type.csv`)
| Column | Description |
|--------|-------------|
| issue_type | Type/category of issue |
| issue_count | Number of resolved issues for the type |
| sla_avg_hours | Average SLA (business hours) for the type |

---

## Optional Azure Cloud Architecture (Managed, Cloud-First)
If this pipeline were deployed on Azure, a managed and scalable architecture could be:

- **Storage (Raw/Bronze/Silver/Gold):** Azure Data Lake Storage Gen2 organized by Medallion layer
- **Ingestion:** Azure Data Factory (Copy Activities) from Blob Storage into ADLS Gen2
- **Processing (lightweight):** Azure Functions or Synapse Serverless for simple transforms
- **Processing (at scale):** Azure Databricks or Synapse Spark for larger volumes and complex transforms
- **Orchestration:** Azure Data Factory or Synapse Pipelines
- **Secrets Management:** Azure Key Vault
- **Monitoring and Observability:** Azure Monitor + Log Analytics

This preserves the Medallion pattern while keeping costs low at small scale and
providing a clear path to Spark-based processing as complexity grows.

---

## Notes
- Each Medallion layer can run independently
- Azure Blob ingestion supports downloading all blobs in a container
- The project is designed for local execution
