"""
test_transform.py

Unit tests for transform_transactions() - confirms derived fields
(date parts, high-value flag, standardized text) are computed correctly.
"""

import pandas as pd
from transform import transform_transactions


def test_derived_date_fields():
    df = pd.DataFrame([{
        "transaction_id": "txn-001",
        "account_id": "ACC1",
        "transaction_type": "PAYMENT",
        "channel": "online",
        "amount": 100.0,
        "currency": "EUR",
        "status": "completed",
        "transaction_timestamp": "2026-03-14T15:30:00",  # a Saturday
    }])

    result = transform_transactions(df)
    row = result.iloc[0]

    assert str(row["transaction_date"]) == "2026-03-14"
    assert row["transaction_hour"] == 15
    assert row["day_of_week"] == "Saturday"
    assert row["is_weekend"] == True


def test_weekday_is_not_flagged_as_weekend():
    df = pd.DataFrame([{
        "transaction_id": "txn-002",
        "account_id": "ACC1",
        "transaction_type": "PAYMENT",
        "channel": "ONLINE",
        "amount": 100.0,
        "currency": "EUR",
        "status": "COMPLETED",
        "transaction_timestamp": "2026-03-11T09:00:00",  # a Wednesday
    }])

    result = transform_transactions(df)
    assert result.iloc[0]["is_weekend"] == False


def test_high_value_flag():
    df = pd.DataFrame([
        {"transaction_id": "txn-a", "account_id": "ACC1", "transaction_type": "PAYMENT",
         "channel": "ONLINE", "amount": 15000.0, "currency": "EUR", "status": "COMPLETED",
         "transaction_timestamp": "2026-01-01T10:00:00"},
        {"transaction_id": "txn-b", "account_id": "ACC1", "transaction_type": "PAYMENT",
         "channel": "ONLINE", "amount": 500.0, "currency": "EUR", "status": "COMPLETED",
         "transaction_timestamp": "2026-01-01T10:00:00"},
    ])

    result = transform_transactions(df)
    assert result.iloc[0]["is_high_value"] == True
    assert result.iloc[1]["is_high_value"] == False


def test_text_standardization():
    df = pd.DataFrame([{
        "transaction_id": "txn-001",
        "account_id": "ACC1",
        "transaction_type": "PAYMENT",
        "channel": "  online  ",
        "amount": 100.0,
        "currency": "EUR",
        "status": "  completed ",
        "transaction_timestamp": "2026-01-01T10:00:00",
    }])

    result = transform_transactions(df)
    row = result.iloc[0]

    assert row["channel"] == "ONLINE"
    assert row["status"] == "COMPLETED"
