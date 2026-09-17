-- analysis_queries.sql
-- Realistic analytical queries against the transactions_clean table,
-- demonstrating window functions, CTEs, and KPI-style reporting logic
-- (matching the kind of queries used for BI dashboards / monitoring
-- described in the project README).

-- ============================================================
-- 1. Daily transaction volume & value trend (KPI monitoring)
-- ============================================================
SELECT
    transaction_date,
    COUNT(*)                         AS transaction_count,
    ROUND(SUM(amount), 2)            AS total_value,
    ROUND(AVG(amount), 2)            AS avg_transaction_value
FROM transactions_clean
GROUP BY transaction_date
ORDER BY transaction_date;


-- ============================================================
-- 2. Month-over-month growth by channel (window function: LAG)
-- ============================================================
WITH monthly_by_channel AS (
    SELECT
        channel,
        DATE_TRUNC('month', transaction_date) AS month,
        SUM(amount)                            AS monthly_total
    FROM transactions_clean
    GROUP BY channel, DATE_TRUNC('month', transaction_date)
)
SELECT
    channel,
    month,
    monthly_total,
    LAG(monthly_total) OVER (PARTITION BY channel ORDER BY month) AS prev_month_total,
    ROUND(
        100.0 * (monthly_total - LAG(monthly_total) OVER (PARTITION BY channel ORDER BY month))
        / NULLIF(LAG(monthly_total) OVER (PARTITION BY channel ORDER BY month), 0),
        2
    ) AS mom_growth_pct
FROM monthly_by_channel
ORDER BY channel, month;


-- ============================================================
-- 3. Top 10 accounts by transaction volume (ranking)
-- ============================================================
SELECT
    account_id,
    COUNT(*)              AS transaction_count,
    ROUND(SUM(amount), 2) AS total_value,
    RANK() OVER (ORDER BY SUM(amount) DESC) AS value_rank
FROM transactions_clean
GROUP BY account_id
ORDER BY value_rank
LIMIT 10;


-- ============================================================
-- 4. High-value transaction monitoring (compliance/AML-style flag)
-- ============================================================
SELECT
    transaction_id,
    account_id,
    amount,
    channel,
    status,
    transaction_timestamp
FROM transactions_clean
WHERE is_high_value = TRUE
ORDER BY amount DESC;


-- ============================================================
-- 5. Data quality summary (rejected vs clean ratio, for a
--    "pipeline health" dashboard panel)
-- ============================================================
WITH totals AS (
    SELECT
        (SELECT COUNT(*) FROM transactions_clean)    AS clean_count,
        (SELECT COUNT(*) FROM transactions_rejected) AS rejected_count
)
SELECT
    clean_count,
    rejected_count,
    clean_count + rejected_count AS total_ingested,
    ROUND(100.0 * clean_count / NULLIF(clean_count + rejected_count, 0), 2) AS pass_rate_pct
FROM totals;


-- ============================================================
-- 6. Rejection reason breakdown (root cause analysis)
-- ============================================================
SELECT
    reject_reason,
    COUNT(*) AS occurrences
FROM transactions_rejected
GROUP BY reject_reason
ORDER BY occurrences DESC;


-- ============================================================
-- 7. Weekend vs weekday transaction behavior comparison
-- ============================================================
SELECT
    is_weekend,
    COUNT(*)                    AS transaction_count,
    ROUND(AVG(amount), 2)       AS avg_amount,
    ROUND(SUM(amount), 2)       AS total_value
FROM transactions_clean
GROUP BY is_weekend;
