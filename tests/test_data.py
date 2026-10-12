import json
from datetime import UTC, datetime
from pathlib import Path

import requests

from core.data import API_URL, fetch_snapshots, load_snapshot

SAMPLE = Path("data/sample.json")


def test_load_snapshot_parses_sample():
    snapshot = load_snapshot(SAMPLE)
    assert snapshot.start_time == datetime(2025, 3, 30, 12, 0, tzinfo=UTC)
    assert snapshot.settlement_period == 25
    assert len(snapshot.generation) == 20
    assert snapshot.generation["WIND"] == 10993
    assert snapshot.generation["PS"] == -1315  # parsing keeps raw values


def test_fetch_snapshots_calls_api_and_parses(monkeypatch):
    calls = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return [json.loads(SAMPLE.read_text())]

    def fake_get(url, params, timeout):
        calls.update(url=url, params=params, timeout=timeout)
        return FakeResponse()

    monkeypatch.setattr(requests, "get", fake_get)
    snapshots = fetch_snapshots(datetime(2025, 3, 23, 12, 0, tzinfo=UTC), datetime(2025, 3, 30, 12, 0, tzinfo=UTC))

    assert [s.generation["WIND"] for s in snapshots] == [10993]
    assert calls["url"] == API_URL
    assert calls["params"] == {
        "startTime": "2025-03-23T12:00:00Z",
        "endTime": "2025-03-30T12:00:00Z",
        "includeNegativeGeneration": "true",
    }
    assert calls["timeout"] == 10
