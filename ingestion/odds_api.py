"""Ingest bookmaker odds from The Odds API into the bronze layer.

Design notes:
- The free tier allows 500 credits/month. Cost per call = markets x regions.
  Each sport below requests 1 market x 2 regions = 2 credits per run.
- Quota headers returned by the API are printed on every call so usage is
  always visible in logs.
- Each row is tagged with snapshot_ts; repeated runs build line-movement
  history in the bronze layer.
- soccer_fifa_world_cup_winner is an outrights (tournament winner) market,
  directly comparable to Polymarket's "Will X win the World Cup" markets.
"""

import os
from datetime import datetime, timezone

import dlt
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.the-odds-api.com/v4/sports"

# sport_key -> market type to request
SPORTS = {
    "soccer_fifa_world_cup": "h2h",
    "soccer_fifa_world_cup_winner": "outrights",
    "tennis_atp_wimbledon": "h2h",
    "tennis_wta_wimbledon": "h2h",
}
REGIONS = "uk,us"


@dlt.resource(name="bookmaker_odds", write_disposition="append")
def bookmaker_odds():
    api_key = os.environ["ODDS_API_KEY"]
    snapshot_ts = datetime.now(timezone.utc).isoformat()

    for sport, market in SPORTS.items():
        url = f"{BASE_URL}/{sport}/odds"
        params = {
            "apiKey": api_key,
            "regions": REGIONS,
            "markets": market,
            "oddsFormat": "decimal",
        }
        resp = requests.get(url, params=params, timeout=30)

        if resp.status_code in (404, 422):
            print(f"[odds_api] skipping {sport}: {resp.status_code} {resp.text[:120]}")
            continue
        resp.raise_for_status()

        used = resp.headers.get("x-requests-used", "?")
        remaining = resp.headers.get("x-requests-remaining", "?")
        print(f"[odds_api] {sport} ({market}): quota used={used}, remaining={remaining}")

        for event in resp.json():
            event["snapshot_ts"] = snapshot_ts
            event["sport_key_requested"] = sport
            event["market_requested"] = market
            yield event


def run() -> None:
    pipeline = dlt.pipeline(
        pipeline_name="betting_markets",
        destination=dlt.destinations.duckdb("data/warehouse.duckdb"),
        dataset_name="bronze",
    )
    load_info = pipeline.run(bookmaker_odds())
    print(load_info)


if __name__ == "__main__":
    run()