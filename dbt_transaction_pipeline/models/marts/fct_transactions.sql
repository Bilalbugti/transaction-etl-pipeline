-- fct_transactions.sql
--
-- Marts layer: the business-ready fact table. Builds on the cleaned
-- staging model and adds derived fields used for reporting - the
-- same kind of logic as transform.py in the Python pipeline, but
-- expressed as SQL running directly in the warehouse.

with staged as (

    select * from {{ ref('stg_transactions') }}

),

final as (

    select
        transaction_id,
        account_id,
        transaction_type,
        channel,
        amount,
        currency,
        status,
        transaction_timestamp,
        cast(transaction_timestamp as date) as transaction_date,
        extract(hour from transaction_timestamp) as transaction_hour,
        strftime(transaction_timestamp, '%A') as day_of_week,
        case
            when extract(dow from transaction_timestamp) in (0, 6) then true
            else false
        end as is_weekend,
        case
            when abs(amount) > 10000 then true
            else false
        end as is_high_value

    from staged
    -- Quality gate: only records passing basic validity and business
    -- rule checks reach the fact table - mirrors the same logic as
    -- the Python pipeline's validate_transactions().
    where account_id is not null
      and transaction_timestamp is not null
      and not (transaction_type = 'DEPOSIT' and amount < 0)

)

select * from final
