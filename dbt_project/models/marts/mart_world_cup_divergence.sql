-- Gold: DraftKings vs Polymarket implied probabilities for World Cup winner,
-- per team per day, with the bookmaker's margin (vig) removed.

with bookmaker as (
    select
        cast(snapshot_ts as date)         as snapshot_date,
        outcome_name                      as team,
        implied_probability               as raw_prob,
        -- normalize so probabilities sum to 1.0 within each snapshot (vig removal)
        implied_probability
            / sum(implied_probability) over (partition by snapshot_ts)
                                          as bookmaker_prob
    from {{ ref('stg_bookmaker_odds') }}
    where sport_key = 'soccer_fifa_world_cup_winner'
      and bookmaker = 'draftkings'
      and market_type = 'outrights'
),

polymarket as (
    select
        cast(snapshot_ts as date)         as snapshot_date,
        world_cup_team                    as team,
        yes_price                         as polymarket_prob
    from {{ ref('stg_polymarket_markets') }}
    where world_cup_team is not null
),

-- one row per team per day from each source (latest values of the day)
bookmaker_daily as (
    select snapshot_date, team,
           avg(bookmaker_prob) as bookmaker_prob,
           avg(raw_prob)       as bookmaker_raw_prob
    from bookmaker
    group by 1, 2
),

polymarket_daily as (
    select snapshot_date, team,
           avg(polymarket_prob) as polymarket_prob
    from polymarket
    group by 1, 2
)

select
    b.snapshot_date,
    b.team,
    round(b.bookmaker_prob, 4)                        as draftkings_prob,
    round(p.polymarket_prob, 4)                       as polymarket_prob,
    round(b.bookmaker_prob - p.polymarket_prob, 4)    as divergence,
    round(abs(b.bookmaker_prob - p.polymarket_prob), 4) as abs_divergence,
    round(b.bookmaker_raw_prob - b.bookmaker_prob, 4) as vig_share
from bookmaker_daily b
join polymarket_daily p
  on b.snapshot_date = p.snapshot_date
 and lower(trim(b.team)) = lower(trim(p.team))