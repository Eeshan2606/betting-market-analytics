-- One row per (snapshot, event, bookmaker, market, outcome).
-- Flattens dlt's nested tables and converts decimal odds to implied probability.

with events as (
    select * from {{ source('bronze', 'bookmaker_odds') }}
),

bookmakers as (
    select * from {{ source('bronze', 'bookmaker_odds__bookmakers') }}
),

markets as (
    select * from {{ source('bronze', 'bookmaker_odds__bookmakers__markets') }}
),

outcomes as (
    select * from {{ source('bronze', 'bookmaker_odds__bookmakers__markets__outcomes') }}
)

select
    e.snapshot_ts,
    e.sport_key_requested                as sport_key,
    e.home_team,
    e.away_team,
    b.key                                as bookmaker,
    m.key                                as market_type,
    o.name                               as outcome_name,
    o.price                              as decimal_odds,
    1.0 / o.price                        as implied_probability
from events e
join bookmakers b on b._dlt_parent_id = e._dlt_id
join markets   m on m._dlt_parent_id = b._dlt_id
join outcomes  o on o._dlt_parent_id = m._dlt_id
where o.price > 1.0