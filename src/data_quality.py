"""
data_quality.py

Automated data quality validation layer for the transaction pipeline.

Mirrors real production data quality checks used before loading records
into a warehouse: completeness, uniqueness, validity, and business-rule
checks. Produces a structured quality report and separates clean records
from rejected ones - clean data proceeds to load, rejected data is
quarantined for investigation (never silently dropped).
"""

import pandas as pd
from dataclasses import dataclass, field
from typing import List


VALID_STATUSES = {"COMPLETED", "PENDING", "FAILED", "REVERSED"}
VALID_CHANNELS = {"ATM", "ONLINE", "BRANCH", "MOBILE", "POS"}


@dataclass
class QualityReport:
    total_records: int = 0
    passed_records: int = 0
    failed_records: int = 0
    issues: dict = field(default_factory=dict)

    def summary(self) -> str:
        lines = [
            "=" * 50,
            "DATA QUALITY REPORT",
            "=" * 50,
            f"Total records processed : {self.total_records}",
            f"Passed validation       : {self.passed_records} "
            f"({self.passed_records / max(self.total_records,1):.1%})",
            f"Failed validation        : {self.failed_records} "
            f"({self.failed_records / max(self.total_records,1):.1%})",
            "-" * 50,
            "Issues breakdown:",
        ]
        for issue, count in self.issues.items():
            lines.append(f"  - {issue}: {count}")
        lines.append("=" * 50)
        return "\n".join(lines)


def validate_transactions(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, QualityReport]:
    """
    Runs a series of data quality checks on the raw transaction dataframe.

    Returns:
        clean_df:    records that passed all checks
        rejected_df: records that failed at least one check, tagged with reason
        report:      summary statistics of the validation run
    """
    report = QualityReport(total_records=len(df))
    df = df.copy()
    df["reject_reason"] = ""

    # Check 1: Completeness - required fields must not be null/empty
    missing_account = df["account_id"].isna() | (df["account_id"] == "")
    df.loc[missing_account, "reject_reason"] += "MISSING_ACCOUNT_ID;"
    report.issues["missing_account_id"] = int(missing_account.sum())

    missing_timestamp = df["transaction_timestamp"].isna() | (df["transaction_timestamp"] == "")
    df.loc[missing_timestamp, "reject_reason"] += "MISSING_TIMESTAMP;"
    report.issues["missing_timestamp"] = int(missing_timestamp.sum())

    # Check 2: Uniqueness - transaction_id must be unique (dedupe, keep first)
    duplicate_ids = df.duplicated(subset="transaction_id", keep="first")
    df.loc[duplicate_ids, "reject_reason"] += "DUPLICATE_TRANSACTION_ID;"
    report.issues["duplicate_transaction_id"] = int(duplicate_ids.sum())

    # Check 3: Validity - status and channel must be from known enum values
    invalid_status = ~df["status"].isin(VALID_STATUSES)
    df.loc[invalid_status, "reject_reason"] += "INVALID_STATUS;"
    report.issues["invalid_status"] = int(invalid_status.sum())

    invalid_channel = ~df["channel"].isin(VALID_CHANNELS)
    df.loc[invalid_channel, "reject_reason"] += "INVALID_CHANNEL;"
    report.issues["invalid_channel"] = int(invalid_channel.sum())

    # Check 4: Business rule - DEPOSIT transactions must not be negative
    bad_deposit = (df["transaction_type"] == "DEPOSIT") & (df["amount"] < 0)
    df.loc[bad_deposit, "reject_reason"] += "NEGATIVE_DEPOSIT_AMOUNT;"
    report.issues["negative_deposit_amount"] = int(bad_deposit.sum())

    # Split clean vs rejected
    is_rejected = df["reject_reason"] != ""
    clean_df = df.loc[~is_rejected].drop(columns=["reject_reason"])
    rejected_df = df.loc[is_rejected]

    report.passed_records = len(clean_df)
    report.failed_records = len(rejected_df)

    return clean_df, rejected_df, report
