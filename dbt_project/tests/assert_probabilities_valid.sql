-- A test passes when it returns zero rows.
select *
from {{ ref('stg_bookmaker_odds') }}
where implied_probability <= 0 or implied_probability >= 1