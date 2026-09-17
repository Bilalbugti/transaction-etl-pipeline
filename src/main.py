"""
main.py

Orchestrates the full ETL pipeline end to end:
  Extract (read raw CSV) -> Validate (data quality) -> Transform -> Load

Run with:
    python src/main.py
"""

import logging
import pandas as pd

from data_quality import validate_transactions
from transform import transform_transactions
from load import load_to_warehouse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("etl_pipeline")

RAW_DATA_PATH = "data/raw_transactions.csv"


def extract(path: str) -> pd.DataFrame:
    logger.info(f"Extracting raw data from {path}")
    df = pd.read_csv(path, dtype=str)  # read as string first; typing happens in transform
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    logger.info(f"Extracted {len(df)} raw records")
    return df


def run_pipeline():
    logger.info("Starting transaction ETL pipeline")

    # Extract
    raw_df = extract(RAW_DATA_PATH)

    # Validate (data quality gate)
    logger.info("Running data quality validation")
    clean_df, rejected_df, report = validate_transactions(raw_df)
    logger.info("\n" + report.summary())

    if len(rejected_df) > 0:
        rejected_df.to_csv("data/rejected_transactions.csv", index=False)
        logger.warning(
            f"{len(rejected_df)} records failed validation and were quarantined "
            f"-> data/rejected_transactions.csv"
        )

    # Transform
    logger.info("Transforming clean records")
    transformed_df = transform_transactions(clean_df)

    # Load
    logger.info("Loading to warehouse")
    load_to_warehouse(transformed_df, rejected_df)

    logger.info("Pipeline completed successfully")


if __name__ == "__main__":
    run_pipeline()
