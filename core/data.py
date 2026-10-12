import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

API_URL = "https://data.elexon.co.uk/bmrs/api/v1/generation/outturn/summary"
TIMEOUT_SECONDS = 10


@dataclass
class Snapshot:
    """Generation by fuel type for one half-hour settlement period."""

    start_time: datetime  # UTC
    settlement_period: int
    generation: dict[str, float]  # MW by fuel type


def parse_snapshot(record: dict[str, Any]) -> Snapshot:
    """Convert one Elexon JSON record into a Snapshot."""
    return Snapshot(
        start_time=datetime.fromisoformat(record["startTime"]),
        settlement_period=record["settlementPeriod"],
        generation={item["fuelType"]: item["generation"] for item in record["data"]},
    )


def load_snapshot(path: Path) -> Snapshot:
    """Read one Elexon JSON record from a file."""
    return parse_snapshot(json.loads(path.read_text()))


def fetch_snapshots(start: datetime, end: datetime) -> list[Snapshot]:
    """Fetch the half-hourly records between two UTC times from the Elexon API, oldest first."""
    params = {
        "startTime": f"{start:%Y-%m-%dT%H:%M:%SZ}",
        "endTime": f"{end:%Y-%m-%dT%H:%M:%SZ}",
        "includeNegativeGeneration": "true",  # match the brief's sample; we clip negatives ourselves
    }
    response = requests.get(API_URL, params=params, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()  # turn HTTP errors (e.g. 500) into exceptions
    return [parse_snapshot(record) for record in response.json()]
