-- schema.sql
-- Target warehouse schema for the transaction analytics layer.
-- Written for Snowflake syntax (production target); works with minor
-- syntax adjustments on most warehouses (SQLite demo uses pandas.to_sql
-- for simplicity - see load.py).

CREATE TABLE IF NOT EXISTS transactions_clean (
    transaction_id       STRING       NOT NULL PRIMARY KEY,
    account_id           STRING       NOT NULL,
    transaction_type     STRING       NOT NULL,
    channel               STRING       NOT NULL,
    amount                NUMBER(12,2) NOT NULL,
    currency              STRING       NOT NULL,
    status                 STRING       NOT NULL,
    transaction_timestamp TIMESTAMP_NTZ NOT NULL,
    transaction_date      DATE,
    transaction_hour       NUMBER(2),
    day_of_week            STRING,
    is_weekend             BOOLEAN,
    is_high_value          BOOLEAN
);

CREATE TABLE IF NOT EXISTS transactions_rejected (
    transaction_id       STRING,
    account_id           STRING,
    transaction_type     STRING,
    channel               STRING,
    amount                NUMBER(12,2),
    currency              STRING,
    status                 STRING,
    transaction_timestamp STRING,
    reject_reason          STRING NOT NULL
);

-- Index recommendations for a real warehouse (Snowflake auto-clusters,
-- but for a row-store DB these would matter):
-- CREATE INDEX idx_txn_account ON transactions_clean(account_id);
-- CREATE INDEX idx_txn_date ON transactions_clean(transaction_date);
