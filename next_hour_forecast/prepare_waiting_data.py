from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
import pandas as pd
import requests

URL = "https://data.elexon.co.uk/bmrs/api/v1/generation/outturn/summary"
NOT_GREEN = {"CCGT", "COAL", "OCGT", "OIL"}


def download_data(days: int = 365) -> list[dict[str, Any]]:
    """Fetch one year in 7-day chunks to preserve 30-minute resolution."""
    end = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start = end - timedelta(days=days)
    rows = []

    while start < end:
        stop = min(start + timedelta(days=7), end)
        response = requests.get(
            URL,
            params={
                "startTime": start.isoformat().replace("+00:00", "Z"),
                "endTime": stop.isoformat().replace("+00:00", "Z"),
                "includeNegativeGeneration": "true",
            },
            timeout=60,
        )
        response.raise_for_status()
        rows.extend(response.json())
        start = stop

    unique = {row["startTime"]: row for row in rows}
    return [unique[t] for t in sorted(unique) if pd.Timestamp(t).minute in (0, 30)]


def build_dataset(raw: list[dict[str, Any]]) -> pd.DataFrame:
    """Create five live features and label whether the next hour is cleaner."""
    rows = []

    for record in raw:
        fuel = {
            item["fuelType"]: max(float(item["generation"]), 0)
            for item in record["data"]
        }
        total = sum(fuel.values())

        rows.append({
            "timestamp": pd.Timestamp(record["startTime"]),
            "not_green": 100 * sum(fuel.get(f, 0) for f in NOT_GREEN) / total,
        })

    df = pd.DataFrame(rows).sort_values("timestamp")

    df["change_30m"] = df["not_green"].diff()
    df["change_2h"] = df["not_green"].diff(4)

    local = df["timestamp"].dt.tz_convert("Europe/London")
    hour = local.dt.hour + local.dt.minute / 60
    df["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    df["hour_cos"] = np.cos(2 * np.pi * hour / 24)

    next_hour = (df["not_green"].shift(-1) + df["not_green"].shift(-2)) / 2
    df["target"] = (next_hour < df["not_green"]).astype(int)

    return df.iloc[:-2].dropna()


def main() -> None:
    """Download and save the prepared modelling dataset."""
    build_dataset(download_data()).to_csv("waiting_data.csv", index=False)


if __name__ == "__main__":
    main()
