-- One row per market per snapshot.
-- Parses the JSON-encoded outcome/price arrays into real columns and keeps
-- the "Yes" price as the market's implied probability.

with raw as (
    select * from {{ source('bronze', 'polymarket_markets') }}
)

select
    snapshot_ts,
    question,
    slug,
    end_date,
    volume_num,
    json_extract_string(outcomes, '$[0]')                            as outcome_yes_label,
    try_cast(json_extract_string(outcome_prices, '$[0]') as double)  as yes_price,
    try_cast(json_extract_string(outcome_prices, '$[1]') as double)  as no_price,
    -- team name for World Cup winner markets, null otherwise
    nullif(regexp_extract(question, 'Will (.+) win the 2026 FIFA World Cup', 1), '') as world_cup_team
from raw
where active = true
  and closed = false
  and outcomes = '["Yes", "No"]'
  and try_cast(json_extract_string(outcome_prices, '$[0]') as double) is not null