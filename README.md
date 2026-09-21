# Transaction ETL Pipeline

An end-to-end ETL pipeline that ingests raw daily transaction data, runs automated data quality validation, transforms it for analytics, and loads it into a warehouse — with a quarantine layer for records that fail validation instead of silently dropping bad data.

This project mirrors production data engineering work I've done processing 5M+ daily transaction records at scale (Snowflake + Python), rebuilt here with synthetic data so it's fully runnable without any confidential or proprietary information.

## Why this project

Manual, Excel-based reporting doesn't scale and doesn't catch data quality issues. This pipeline demonstrates the pattern I use to replace that: automated ingestion → validation gate → transformation → load, with every rejected record logged and explained rather than silently discarded.

## Architecture

```
raw_transactions.csv
        │
        ▼
   [ EXTRACT ]   src/main.py → extract()
        │
        ▼
[ DATA QUALITY GATE ]   src/data_quality.py
   ├── Completeness checks (required fields)
   ├── Uniqueness checks (duplicate detection)
   ├── Validity checks (enum/domain values)
   └── Business rule checks (e.g. no negative deposits)
        │
   ┌────┴────┐
   ▼         ▼
 CLEAN    REJECTED
   │      (quarantined, logged with reason)
   ▼
[ TRANSFORM ]   src/transform.py
   ├── Type casting & standardization
   └── Derived fields (date parts, high-value flag, etc.)
        │
        ▼
   [ LOAD ]   src/load.py
        │
        ▼
   warehouse.db (SQLite demo / Snowflake in production)
```

## Tech stack

- **Python** (pandas) — extraction, validation, transformation orchestration
- **SQL** — analytical queries (window functions, CTEs, KPI reporting) — see `sql/analysis_queries.sql`
- **SQLite** — local warehouse target for this demo (production target: **Snowflake** — see Production Notes below)

## Results (on the 20,000-record synthetic dataset)

| Metric | Value |
|---|---|
| Records processed | 20,200 |
| Passed validation | 19,187 (95.0%) |
| Quarantined (failed validation) | 1,013 (5.0%) |
| Top rejection reason | Negative deposit amount (523 records) |

Every rejected record is logged with a specific reason (`data/rejected_transactions.csv`), not just dropped — enabling root-cause follow-up with upstream data sources, matching how I handle data quality issues in production.

## How to run it

```bash
git clone https://github.com/YOUR-USERNAME/transaction-etl-pipeline.git
cd transaction-etl-pipeline
pip install -r requirements.txt

# Generate synthetic sample data (or use the pre-generated data/raw_transactions.csv)
python src/generate_sample_data.py

# Run the full pipeline
python src/main.py
```

This will print a full data quality report to the console and load results into `data/warehouse.db`.

## Project structure

```
transaction-etl-pipeline/
├── README.md
├── requirements.txt
├── .gitignore
├── data/
│   └── raw_transactions.csv       # synthetic sample data (tracked for reviewers)
├── src/
│   ├── generate_sample_data.py    # synthetic data generator
│   ├── data_quality.py            # validation layer
│   ├── transform.py               # transformation logic
│   ├── load.py                    # warehouse load logic
│   └── main.py                    # pipeline orchestration
└── sql/
    ├── schema.sql                 # warehouse table definitions
    └── analysis_queries.sql       # window functions, CTEs, KPI queries
```

## Production notes

In the production version of this pattern (Snowflake-based):
- `load.py`'s SQLite connection is swapped for the `snowflake-connector-python` client, with credentials pulled from environment variables (never hardcoded — see `.gitignore`).
- The pipeline runs on a schedule via an orchestrator (Airflow), not manually.
- Data quality thresholds trigger alerts (e.g. Slack/email) if the failure rate exceeds a set threshold, rather than just logging.

## Docker

This pipeline is containerized, so it runs identically on any machine — no need to install Python or pandas locally, just Docker.

### Why

Manually sharing this project meant asking teammates to install the exact right Python version and dependencies themselves — a common source of "works on my machine" failures. Docker packages the pipeline, its dependencies, and the runtime environment into a single portable image.

### What's in the Dockerfile

```dockerfile
FROM python:3.11-slim       # Start from a clean, official Python environment
WORKDIR /app                 # Set the working directory inside the container
COPY requirements.txt .      # Copy dependency list first (caching optimization)
RUN pip install --no-cache-dir -r requirements.txt
COPY . .                     # Copy the rest of the project files
CMD ["python", "src/main.py"]  # Run the pipeline when the container starts
```

### How to build and run it

```bash
git clone https://github.com/Bilalbugti/transaction-etl-pipeline.git
cd transaction-etl-pipeline

# Build the image
docker build -t transaction-etl-pipeline .

# Run the pipeline inside a container
docker run transaction-etl-pipeline
```

You should see the same data quality report and pipeline logs shown in the "Results" section above — except now running fully isolated inside the container, with zero local setup beyond having Docker installed.

## Roadmap

- [x] Containerize with Docker
- [ ] Add Airflow DAG for scheduled orchestration
- [ ] Add dbt models for the transformation layer
- [ ] Add unit tests (pytest) for validation rules

---
*Note: All data in this repository is synthetically generated for demonstration purposes. No real customer, account, or transaction data is used.*
