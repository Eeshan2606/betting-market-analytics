-- A test passes when it returns zero rows.
select *
from {{ ref('stg_polymarket_markets') }}
where yes_price < 0 or yes_price > 1
   or (yes_price + no_price) not between 0.95 and 1.05