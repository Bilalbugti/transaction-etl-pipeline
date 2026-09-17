"""
transform.py

Transformation layer: takes clean, validated transaction records and
prepares them for loading into the analytics layer - type casting,
derived fields, and standardization. This mirrors the "T" in ETL,
typically done in SQL/Snowflake in production, done here in pandas
for a portable, runnable demo.
"""

import pandas as pd


def transform_transactions(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Standardize types
    df["transaction_timestamp"] = pd.to_datetime(df["transaction_timestamp"])
    df["amount"] = df["amount"].astype(float)

    # Derived fields commonly needed for downstream reporting/BI
    df["transaction_date"] = df["transaction_timestamp"].dt.date
    df["transaction_hour"] = df["transaction_timestamp"].dt.hour
    df["day_of_week"] = df["transaction_timestamp"].dt.day_name()
    df["is_weekend"] = df["transaction_timestamp"].dt.dayofweek >= 5

    # Business classification: flag high-value transactions (> 10,000 EUR)
    # commonly used for compliance/AML monitoring style reporting
    df["is_high_value"] = df["amount"].abs() > 10_000

    # Standardize categorical text
    df["channel"] = df["channel"].str.upper().str.strip()
    df["status"] = df["status"].str.upper().str.strip()

    return df
