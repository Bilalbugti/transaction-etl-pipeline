-- stg_transactions.sql
--
-- Staging layer: light cleaning and type casting of the raw
-- transaction seed data. Staging models do minimal transformation -
-- just standardizing types and names - so downstream models can
-- build on a clean, consistent foundation.

with source as (

    select * from {{ ref('raw_transactions') }}

),

cleaned as (

    select
        transaction_id,
        nullif(trim(account_id), '') as account_id,
        transaction_type,
        upper(trim(channel)) as channel,
        cast(amount as double) as amount,
        currency,
        upper(trim(status)) as status,
        cast(transaction_timestamp as timestamp) as transaction_timestamp,
        -- Flags the first occurrence of each transaction_id; duplicates
        -- (from upstream retry/duplication issues) get row_num > 1
        row_number() over (
            partition by transaction_id
            order by transaction_timestamp
        ) as row_num

    from source

),

deduplicated as (

    select
        transaction_id,
        account_id,
        transaction_type,
        channel,
        amount,
        currency,
        status,
        transaction_timestamp
    from cleaned
    where row_num = 1

)

select * from deduplicated
