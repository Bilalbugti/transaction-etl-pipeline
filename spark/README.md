# Spark Transaction Analysis

Demonstrates the transaction pipeline's data quality and analytical logic reimplemented using **Spark's distributed DataFrame API**, as a comparison to the pandas-based approach in the main `transaction-etl-pipeline` project.

## Why Spark

pandas (used in the main pipeline) loads all data into memory on a single machine — fine for the ~20,000-row demo dataset here, but not viable at real production scale (5M+ daily records, growing over time). Spark splits data and computation across multiple machines, so no single machine needs to hold everything in memory at once.

This project uses the same small dataset as the rest of the portfolio (for a runnable, credential-free demo), but the code is written the way it would be at real scale — using Spark's distributed DataFrame API and lazy evaluation model, not because this specific dataset needs it, but to demonstrate the approach.

## Why Docker for this one

Installing Spark natively on Windows requires Java, environment variables, and a Hadoop compatibility file (`winutils.exe`) — a notoriously fiddly setup. Running it in Docker (Java + PySpark pre-installed in the image) avoids all of that, consistent with the Docker-first approach used elsewhere in this portfolio.

## What the job does

1. **Extract** — reads the raw transaction CSV (lazily — Spark builds a query plan, doesn't execute yet)
2. **Deduplicate** — a distributed window function removes duplicate `transaction_id`s, same logic as the pandas/dbt versions
3. **Validate** — filters out records with missing fields or business-rule violations (negative deposits)
4. **Aggregate** — groups by channel to compute transaction volume and value
5. **Rank** — a window function ranks accounts by total transaction value
6. **Explain** — prints Spark's physical execution plan, showing how it distributes the work
7. **Write** — outputs results as **Parquet** (a columnar format standard for large-scale data, much more efficient than CSV at real scale)

## Results (on the 20,200-record dataset)

| Stage | Records |
|---|---|
| Raw | 20,200 |
| After deduplication | 20,000 (200 duplicates removed) |
| After validity + business rule checks | 19,226 |
| **Overall pass rate** | **95.2%** |

Consistent with the pass rate from the pandas and dbt versions of this same validation logic — confirming all three implementations agree.

## How to run it

```bash
git clone https://github.com/Bilalbugti/transaction-etl-pipeline.git
cd transaction-etl-pipeline/spark

docker build -t spark-transaction-analysis .
docker run spark-transaction-analysis
```

## A note on the ranking window function

The account-ranking step uses a global `Window.orderBy()` with no partition, which Spark flags with a performance warning (it has to collapse all data to a single partition to compute an exact global rank). This is called out deliberately rather than hidden — at real scale, you'd either accept that cost for an infrequent report, or use an approximate ranking method if it needed to run frequently on much larger data.

## Tech stack

PySpark 4.0 (Spark's Python API), running in local mode (`local[*]`) inside Docker — the same DataFrame API and concepts apply identically against a real cluster (Databricks, EMR, etc.), just with a different `.master()` configuration.
