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

## Airflow

The pipeline is orchestrated with Apache Airflow — scheduled to run automatically rather than requiring a manual `python src/main.py` trigger, with each stage tracked, logged, and retryable independently.

### Why

A pipeline that only runs when someone remembers to trigger it manually isn't production-ready. Airflow turns Extract, Validate, Transform, and Load into a proper **DAG** (Directed Acyclic Graph) — a defined sequence of tasks with dependencies — scheduled to run daily, with a UI showing exactly what succeeded, failed, and when.

### How it's wired up

The DAG (`airflow/dags/transaction_etl_dag.py`) doesn't reimplement the pipeline logic — it imports and calls the real functions from `src/data_quality.py`, `src/transform.py`, and `src/load.py` directly, via a Docker volume mount. Each pipeline stage becomes its own Airflow task:

```
extract() >> validate() >> transform() >> load()
```

Each task only starts after the previous one succeeds, and Airflow's UI visualizes this dependency graph directly.

### How to run it

```bash
cd airflow
docker-compose up airflow-init    # first time only - sets up the database
docker-compose up -d              # starts the scheduler, webserver, and database
```

Then open `http://localhost:8080` (login: `admin` / `admin`), find the `transaction_etl_pipeline` DAG, unpause it, and trigger it manually — or let it run on its own daily schedule (`0 2 * * *`, 2 AM).

## dbt (Data Build Tool)

The transformation layer is also implemented in dbt — SQL-based models with automated data quality tests, running directly in the warehouse rather than pulling data out into Python.

### Why

The Python transformation step (`transform.py`) works, but it has no built-in testing, no auto-generated documentation, and runs outside the warehouse. dbt addresses all three: transformations are plain SQL, tests are declared alongside the models they test, and everything runs where the data already lives.

### Model structure

```
raw_transactions (seed)
        │
        ▼
stg_transactions      -- cleans types, deduplicates by transaction_id
        │
        ▼
fct_transactions       -- derived fields (date, hour, high-value flag),
                           filtered by the same quality rules as the
                           Python pipeline's validate_transactions()
```

### Tests

9 automated tests run on every `dbt test` — uniqueness and not-null checks on key columns, accepted-value checks on `status` and `channel`, and a custom test (`tests/no_negative_deposits.sql`) mirroring the same business rule check as the Python pipeline: a DEPOSIT transaction should never have a negative amount.

### How to run it

```bash
pip install dbt-core dbt-duckdb
cd dbt_transaction_pipeline

dbt seed    # loads the raw transaction data
dbt run     # builds the staging and marts models
dbt test    # runs all 9 data quality tests
```

This demo uses DuckDB (a local, file-based database) so it runs without any cloud credentials — the same dbt code runs against Snowflake in production with just a different `profiles.yml` target.

## Spark

The pipeline's data quality and analytical logic is also implemented using PySpark's distributed DataFrame API — demonstrating the approach used once data outgrows what pandas can handle on a single machine.

### Why

pandas loads all data into memory on one machine — fine for this demo's ~20,000 rows, but not viable at the production scale this pipeline is modeled on (5M+ daily records, growing over time). Spark distributes data and computation across multiple machines, so no single machine needs to hold everything in memory.

### What it does

Extract → deduplicate (distributed window function) → validate (same business rules as the Python/dbt versions) → aggregate by channel → rank top accounts by value (window function) → write results as Parquet. All three implementations (pandas, dbt, Spark) agree on the same 95%+ pass rate against the same data.

### How to run it

Runs in Docker to avoid native Java/Spark setup on Windows:

```bash
cd spark
docker build -t spark-transaction-analysis .
docker run spark-transaction-analysis
```

See [`spark/README.md`](spark/README.md) for full details, including a deliberate note on a Spark performance warning encountered in the ranking step.

## Roadmap

- [x] Containerize with Docker
- [x] Add Airflow DAG for scheduled orchestration
- [x] Add dbt models for the transformation layer
- [x] Add a Spark version of the pipeline for distributed processing at scale
- [ ] Add unit tests (pytest) for validation rules

---
*Note: All data in this repository is synthetically generated for demonstration purposes. No real customer, account, or transaction data is used.*
