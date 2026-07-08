# Backlog

## Next session
- Dashboard editorial redesign: five-act narrative structure
  (1 The Race: hero + auto-generated headline + deltas;
   2 The Matches: semifinal h2h matchup cards;
   3 The Movers: polymarket one_day/one_week price-change fields;
   4 The Disagreement: relative divergence callouts + colored table;
   5 The House Edge: vig infographic incl. exchange back/lay spread)
  plus methodology expander. May need silver model for h2h match odds.
- Public hosting, option A: parquet extract committed to repo,
  app reads parquet if present else warehouse; Streamlit Community Cloud.
- README
- Phase 5: Dockerfile + docker-compose, GitHub Actions CI (lint + dbt build)

## Post-MVP
- Outcome resolution + calibration scoring (Brier) per market
- Divergence alerting: relative/statistical thresholds, crossing detection,
  cooldown, alert history table; Dagster sensor + Telegram/Slack delivery
- Lead-lag analysis: which market moves first around news events
- LLM extraction: news/injury feeds -> structured events -> join to price moves
- Embedding-based entity resolution for team/player names
- Auto-generated daily market briefing from gold tables
- Streaming ingestion: Polymarket WebSocket -> Kafka/Redpanda
- BigQuery production target (dev/prod dbt split)
