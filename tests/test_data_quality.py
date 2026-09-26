"""
test_data_quality.py

Unit tests for the data quality validation layer (data_quality.py).
Each test builds a small, deliberately crafted DataFrame with a known
issue, and confirms validate_transactions() catches exactly that issue
- not a broader integration test against the full 20K-record dataset,
but targeted tests of each individual validation rule.
"""

import pandas as pd
import pytest
from data_quality import validate_transactions


def make_base_row(**overrides):
    """A single valid transaction row, with fields overridable per test."""
    row = {
        "transaction_id": "txn-001",
        "account_id": "ACC123456",
        "transaction_type": "PAYMENT",
        "channel": "ONLINE",
        "amount": 100.0,
        "currency": "EUR",
        "status": "COMPLETED",
        "transaction_timestamp": "2026-01-01T10:00:00",
    }
    row.update(overrides)
    return row


def test_valid_record_passes():
    df = pd.DataFrame([make_base_row()])
    clean_df, rejected_df, report = validate_transactions(df)

    assert len(clean_df) == 1
    assert len(rejected_df) == 0
    assert report.passed_records == 1
    assert report.failed_records == 0


def test_missing_account_id_is_rejected():
    df = pd.DataFrame([make_base_row(account_id="")])
    clean_df, rejected_df, report = validate_transactions(df)

    assert len(clean_df) == 0
    assert len(rejected_df) == 1
    assert report.issues["missing_account_id"] == 1


def test_missing_timestamp_is_rejected():
    df = pd.DataFrame([make_base_row(transaction_timestamp="")])
    clean_df, rejected_df, report = validate_transactions(df)

    assert len(clean_df) == 0
    assert report.issues["missing_timestamp"] == 1


def test_duplicate_transaction_id_keeps_first_rejects_rest():
    df = pd.DataFrame([
        make_base_row(transaction_id="txn-dup", amount=100.0),
        make_base_row(transaction_id="txn-dup", amount=200.0),
    ])
    clean_df, rejected_df, report = validate_transactions(df)

    assert len(clean_df) == 1
    assert len(rejected_df) == 1
    assert report.issues["duplicate_transaction_id"] == 1
    # the first occurrence should be the one that survives
    assert clean_df.iloc[0]["amount"] == 100.0


def test_invalid_status_is_rejected():
    df = pd.DataFrame([make_base_row(status="NOT_A_REAL_STATUS")])
    clean_df, rejected_df, report = validate_transactions(df)

    assert len(clean_df) == 0
    assert report.issues["invalid_status"] == 1


def test_invalid_channel_is_rejected():
    df = pd.DataFrame([make_base_row(channel="CARRIER_PIGEON")])
    clean_df, rejected_df, report = validate_transactions(df)

    assert len(clean_df) == 0
    assert report.issues["invalid_channel"] == 1


def test_negative_deposit_is_rejected():
    df = pd.DataFrame([make_base_row(transaction_type="DEPOSIT", amount=-50.0)])
    clean_df, rejected_df, report = validate_transactions(df)

    assert len(clean_df) == 0
    assert report.issues["negative_deposit_amount"] == 1


def test_negative_withdrawal_is_allowed():
    """A negative amount is only invalid for DEPOSIT - other transaction
    types (e.g. WITHDRAWAL) are allowed to be negative."""
    df = pd.DataFrame([make_base_row(transaction_type="WITHDRAWAL", amount=-50.0)])
    clean_df, rejected_df, report = validate_transactions(df)

    assert len(clean_df) == 1
    assert len(rejected_df) == 0


def test_report_summary_contains_key_figures():
    df = pd.DataFrame([make_base_row(), make_base_row(account_id="")])
    _, _, report = validate_transactions(df)
    summary = report.summary()

    assert "Total records processed : 2" in summary
    assert "Passed validation" in summary
