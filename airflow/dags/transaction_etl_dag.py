"""
transaction_etl_dag.py

Airflow DAG that orchestrates the transaction ETL pipeline - the same
Extract -> Validate -> Transform -> Load pipeline from
transaction-etl-pipeline/src/, now scheduled and orchestrated by
Airflow instead of being run manually with `python src/main.py`.

This DAG doesn't reimplement the pipeline logic - it imports and calls
the real functions from data_quality.py, transform.py, and load.py,
which are mounted into the container from the actual project folder.
Each pipeline stage becomes a separate Airflow task, so Airflow can
retry, log, and monitor each stage independently.
"""

from __future__ import annotations

import sys
import pendulum
from airflow.decorators import dag, task

# The real project's src/ folder is mounted into the container at this
# path (see docker-compose.yaml volumes) - adding it to sys.path lets
# us import the actual pipeline modules directly.
PROJECT_SRC = "/opt/airflow/project/src"
if PROJECT_SRC not in sys.path:
    sys.path.insert(0, PROJECT_SRC)

RAW_DATA_PATH = "/opt/airflow/project/data/raw_transactions.csv"
DB_PATH = "/opt/airflow/project/data/warehouse.db"


@dag(
    dag_id="transaction_etl_pipeline",
    description="Extract -> Validate -> Transform -> Load for transaction data, orchestrated by Airflow",
    schedule="0 2 * * *",  # Every day at 2 AM
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    tags=["etl", "portfolio", "data-quality"],
)
def transaction_etl_pipeline():

    @task
    def extract() -> str:
        """Read the raw transaction CSV. Returns JSON so it can pass
        between tasks via Airflow's XCom (task communication)."""
        import pandas as pd

        df = pd.read_csv(RAW_DATA_PATH, dtype=str)
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        print(f"Extracted {len(df)} raw records")
        return df.to_json()

    @task
    def validate(raw_json: str) -> dict:
        """Run the same data quality validation used in the standalone
        pipeline - completeness, uniqueness, validity, business rules."""
        import pandas as pd
        from data_quality import validate_transactions

        df = pd.read_json(raw_json)
        clean_df, rejected_df, report = validate_transactions(df)
        print(report.summary())
        return {"clean": clean_df.to_json(), "rejected": rejected_df.to_json()}

    @task
    def transform(validated: dict) -> dict:
        """Apply the same transformation logic - type casting, derived
        fields - to the clean records only."""
        import pandas as pd
        from transform import transform_transactions

        clean_df = pd.read_json(validated["clean"])
        transformed_df = transform_transactions(clean_df)
        return {"transformed": transformed_df.to_json(), "rejected": validated["rejected"]}

    @task
    def load(payload: dict) -> None:
        """Load clean, transformed records and rejected records into
        the warehouse - same load_to_warehouse() function as the
        standalone pipeline."""
        import pandas as pd
        from load import load_to_warehouse

        transformed_df = pd.read_json(payload["transformed"])
        rejected_df = pd.read_json(payload["rejected"])
        load_to_warehouse(transformed_df, rejected_df, db_path=DB_PATH)

    # Task dependencies - this is the actual DAG (Directed Acyclic
    # Graph): each task only starts after the one before it succeeds.
    raw = extract()
    validated = validate(raw)
    transformed = transform(validated)
    load(transformed)


transaction_etl_pipeline()
