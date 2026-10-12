from datetime import UTC, datetime, timedelta
from typing import Any

from core.calculations import GridSummary, summarise_grid
from core.config import PROJECT_ROOT
from core.data import fetch_snapshots, load_snapshot


def load_summary(config: dict[str, Any]) -> GridSummary | None:
    """Get data from the API or a file (per config) and summarise it; None if no data."""
    if config["data_source"] != "api":
        return summarise_grid(load_snapshot(PROJECT_ROOT / config["data_source"]), config) 
    end = datetime.now(UTC)
    history = fetch_snapshots(end - timedelta(days=config["baseline"]["lookback_days"]), end)
    if not history:
        return None
    return summarise_grid(history[-1], config, history[:-1])  # newest = now; earlier = history
