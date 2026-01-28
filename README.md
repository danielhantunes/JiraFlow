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
| **Bronze** | Normalize and flatten JSON, select and rename key fields (Parquet output) |
| **Silver** | Clean data, convert date fields, filter Open / Done / Resolved issues |
| **Gold** | Keep only Done / Resolved issues and compute SLA metrics |

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
│   └── gold/
├── src/
│   ├── ingestion/   # Raw data ingestion
│   ├── bronze/      # Normalization and field selection
│   ├── silver/      # Cleaning and filtering
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

### Provide input data
Place the Jira export file in the project root:

```text
jira_issues_raw.json
```

Or configure a custom filename using environment variables.

---

### Run the full pipeline
```bash
python -m src.main
```

Each layer can also be executed independently via its corresponding module.

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
- RAW_INPUT_FILENAME (default: jira_issues_raw.txt)
- AZURE_BLOB_PREFIX (downloads all blobs if empty)
- HOLIDAY_API_URL (default: https://date.nager.at/api/v3/PublicHolidays)
- HOLIDAY_COUNTRY_CODE (default: BR)

---

## ⚙️ Local Setup
Copy the example environment file and fill in your values:

```bash
cp .env.example .env
```

Environment variables are loaded locally using `python-dotenv`.

---

## 🔍 Optional: Bronze Data Profiling

The Bronze layer includes **lightweight data profiling utilities** to perform a quick quality check before moving data to Silver.

### Metrics
- Percentage of null values per column
- Column cardinality
- Top values for key categorical fields

### Run
```bash
python run_bronze_profile.py
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

This step is optional but recommended as a **quality gate between Bronze and Silver**.

---

## SLA Calculation Logic
- SLA is calculated as **resolution time in business hours**
- Business hours exclude weekends and national holidays
- Open issues are excluded from SLA metrics
- SLA is considered **met** when:

```
actual_hours ≤ expected_hours
```

---

## Final Gold Schema
- issue_id
- issue_type
- assignee
- priority
- created_at
- resolved_at
- resolution_time_business_hours
- expected_sla_hours
- sla_status

---

## Notes
- Each Medallion layer can run independently
- Azure Blob ingestion supports downloading all blobs in a container
- The project is designed for local execution
