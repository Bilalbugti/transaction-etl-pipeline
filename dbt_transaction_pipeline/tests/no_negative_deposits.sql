-- no_negative_deposits.sql
--
-- Custom dbt test: a DEPOSIT transaction should never have a negative
-- amount. dbt tests pass when this query returns ZERO rows - any row
-- returned here represents a failing record. This mirrors the same
-- business rule check as the Python pipeline's data_quality.py, now
-- expressed as a dbt test that runs automatically on every `dbt test`.

select
    transaction_id,
    transaction_type,
    amount
from {{ ref('fct_transactions') }}
where transaction_type = 'DEPOSIT'
  and amount < 0
