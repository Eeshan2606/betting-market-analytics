"""Ingest live Polymarket prediction-market data into the bronze layer.

Each run appends a timestamped snapshot of the most-traded active markets.
Over many runs, these snapshots become the price-history dataset that
powers line-movement analysis downstream.
"""

from datetime import datetime, timezone

import dlt
import requests

GAMMA_URL = "https://gamma-api.polymarket.com/markets"
PAGE_SIZE = 100
MAX_MARKETS = 300


@dlt.resource(name="polymarket_markets", write_disposition="append")
def polymarket_markets():
    """Yield active markets ordered by volume, tagged with a snapshot time."""
    snapshot_ts = datetime.now(timezone.utc).isoformat()
    offset = 0

    while offset < MAX_MARKETS:
        params = {
            "active": "true",
            "closed": "false",
            "order": "volumeNum",
            "ascending": "false",
            "limit": PAGE_SIZE,
            "offset": offset,
        }
        resp = requests.get(GAMMA_URL, params=params, timeout=30)
        resp.raise_for_status()
        batch = resp.json()

        if not batch:
            break

        for market in batch:
            market["snapshot_ts"] = snapshot_ts
            yield market

        offset += len(batch)


def run() -> None:
    pipeline = dlt.pipeline(
        pipeline_name="betting_markets",
        destination=dlt.destinations.duckdb("data/warehouse.duckdb"),
        dataset_name="bronze",
    )
    load_info = pipeline.run(polymarket_markets())
    print(load_info)


if __name__ == "__main__":
    run()