"""
load.py

Loads transformed transaction data into a local analytical database.

In production (as in the real pipeline this demo is based on) this
target would be Snowflake. For a portable, zero-credential public demo,
this uses SQLite - same relational load pattern, no cloud account
required to run it. Swapping the connection logic for a Snowflake
connector is a drop-in change (see README "Production Notes").
"""

import sqlite3
import pandas as pd

DB_PATH = "data/warehouse.db"


def load_to_warehouse(clean_df: pd.DataFrame, rejected_df: pd.DataFrame, db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)
    try:
        clean_df.to_sql("transactions_clean", conn, if_exists="replace", index=False)
        rejected_df.to_sql("transactions_rejected", conn, if_exists="replace", index=False)
        conn.commit()
        print(f"Loaded {len(clean_df)} clean records -> transactions_clean")
        print(f"Loaded {len(rejected_df)} rejected records -> transactions_rejected (quarantine)")
    finally:
        conn.close()
