"""Dagster definitions: asset graph, dbt integration, and refresh schedule."""

import sys
from pathlib import Path

from dagster import (
    AssetExecutionContext,
    AssetKey,
    AssetSelection,
    Definitions,
    ScheduleDefinition,
    asset,
    define_asset_job,
)
from dagster_dbt import (
DagsterDbtTranslator, 
DagsterDbtTranslatorSettings,
DbtCliResource, 
DbtProject, 
dbt_assets
)


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ingestion.odds_api import run as load_bookmaker_odds  # noqa: E402
from ingestion.polymarket import run as load_polymarket  # noqa: E402

dbt_project = DbtProject(
    project_dir=ROOT / "dbt_project",
    profiles_dir=ROOT / "dbt_project",
)
dbt_project.prepare_if_dev()


@asset(group_name="ingestion")
def polymarket_raw() -> None:
    """Snapshot active Polymarket markets into bronze."""
    load_polymarket()


@asset(group_name="ingestion")
def bookmaker_odds_raw() -> None:
    """Snapshot bookmaker odds into bronze. Quota-metered upstream."""
    load_bookmaker_odds()


class SourceMappingTranslator(DagsterDbtTranslator):
    """Map dbt bronze sources onto the ingestion assets that produce them."""

    def get_asset_key(self, dbt_resource_props):
        if dbt_resource_props["resource_type"] == "source":
            name = dbt_resource_props["name"]
            if name.startswith("bookmaker_odds"):
                return AssetKey("bookmaker_odds_raw")
            if name.startswith("polymarket"):
                return AssetKey("polymarket_raw")
        return super().get_asset_key(dbt_resource_props)


@dbt_assets(
    manifest=dbt_project.manifest_path,
    dagster_dbt_translator=SourceMappingTranslator(
        settings=DagsterDbtTranslatorSettings(enable_duplicate_source_asset_keys=True),
    ),
)
def dbt_models(context: AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()


market_refresh = define_asset_job(
    "market_refresh",
    selection=AssetSelection.all(),
    config={
        "execution": {
            "config": {
                "multiprocess": {"max_concurrent": 1},
            }
        }
    },
)

market_refresh_schedule = ScheduleDefinition(
    job=market_refresh,
    cron_schedule="0 8,20 * * *",
    execution_timezone="Europe/London",
)

defs = Definitions(
    assets=[polymarket_raw, bookmaker_odds_raw, dbt_models],
    schedules=[market_refresh_schedule],
    resources={"dbt": DbtCliResource(project_dir=dbt_project)},
)