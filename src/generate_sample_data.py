"""
generate_sample_data.py

Generates realistic SYNTHETIC transaction data for the ETL pipeline demo.
No real customer or company data is used anywhere in this project.

Simulates the kind of daily transaction feed a bank / financial
outsourcing operation would receive: transaction id, account, amount,
channel, status, timestamp - including intentional "dirty data"
(nulls, duplicates, bad values) so the pipeline has real validation
work to do, matching production data quality issues.
"""

import csv
import random
import uuid
from datetime import datetime, timedelta

random.seed(42)

NUM_RECORDS = 20_000
OUTPUT_PATH = "data/raw_transactions.csv"

CHANNELS = ["ATM", "ONLINE", "BRANCH", "MOBILE", "POS"]
STATUSES = ["COMPLETED", "PENDING", "FAILED", "REVERSED"]
TRANSACTION_TYPES = ["DEPOSIT", "WITHDRAWAL", "TRANSFER", "PAYMENT"]

def random_timestamp(days_back=30):
    start = datetime.now() - timedelta(days=days_back)
    random_seconds = random.randint(0, days_back * 24 * 60 * 60)
    return start + timedelta(seconds=random_seconds)

def generate_account_id():
    return f"ACC{random.randint(100000, 999999)}"

def generate_row():
    return {
        "transaction_id": str(uuid.uuid4()),
        "account_id": generate_account_id(),
        "transaction_type": random.choice(TRANSACTION_TYPES),
        "channel": random.choice(CHANNELS),
        "amount": round(random.uniform(-5000, 50000), 2),
        "currency": "EUR",
        "status": random.choice(STATUSES),
        "transaction_timestamp": random_timestamp().isoformat(),
    }

def inject_data_quality_issues(rows):
    """Deliberately dirty ~5% of records to simulate real-world feed issues."""
    n = len(rows)

    # Nulls in account_id (simulate upstream system glitch)
    for i in random.sample(range(n), k=int(n * 0.01)):
        rows[i]["account_id"] = ""

    # Negative amounts that shouldn't be negative for DEPOSIT type (bad data)
    for i in random.sample(range(n), k=int(n * 0.005)):
        rows[i]["transaction_type"] = "DEPOSIT"
        rows[i]["amount"] = -abs(rows[i]["amount"])

    # Duplicate transaction_ids (simulate upstream retry/duplication bug)
    dup_indices = random.sample(range(n), k=int(n * 0.01))
    for i in dup_indices:
        dup_row = dict(rows[i])
        rows.append(dup_row)

    # Missing timestamps
    for i in random.sample(range(n), k=int(n * 0.003)):
        rows[i]["transaction_timestamp"] = ""

    # Invalid status values (upstream enum drift)
    for i in random.sample(range(n), k=int(n * 0.002)):
        rows[i]["status"] = "UNKNOWN_STATUS"

    random.shuffle(rows)
    return rows

def main():
    rows = [generate_row() for _ in range(NUM_RECORDS)]
    rows = inject_data_quality_issues(rows)

    fieldnames = list(rows[0].keys())
    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows)} synthetic transaction records -> {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
