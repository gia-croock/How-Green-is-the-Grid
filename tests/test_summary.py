from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import requests

import core.summary
from core.config import load_config
from core.data import Snapshot, load_snapshot
from core.summary import load_summary

SAMPLE = load_snapshot(Path("data/sample.json"))  # 9.8% not green
PREVIOUS_HALF_HOUR = Snapshot(datetime(2025, 3, 30, 11, 30, tzinfo=UTC), 24, {"CCGT": 300, "WIND": 700})  # 30%


def make_config(data_source: str) -> dict:
    config = load_config()
    config["data_source"] = data_source
    config["baseline"]["mode"] = "dynamic"
    return config


def test_load_summary_api_mode_uses_newest_and_history(monkeypatch):
    calls = {}

    def fake_fetch(start, end):
        calls.update(start=start, end=end)
        return [PREVIOUS_HALF_HOUR, SAMPLE]

    monkeypatch.setattr(core.summary, "fetch_snapshots", fake_fetch)
    summary = load_summary(make_config("api"))

    assert summary.percentages["green"] == pytest.approx(76.8, abs=0.05)  # newest = now
    assert summary.baseline_percent == pytest.approx(30)  # earlier records = history; now excluded
    assert calls["end"] - calls["start"] == timedelta(days=7)


def test_load_summary_file_mode_uses_static_baseline():
    summary = load_summary(make_config("data/sample.json"))
    assert summary.percentages["green"] == pytest.approx(76.8, abs=0.05)
    assert summary.baseline_percent == 27  # a file has no history


def test_load_summary_returns_none_for_empty_api_response(monkeypatch):
    monkeypatch.setattr(core.summary, "fetch_snapshots", lambda start, end: [])
    assert load_summary(make_config("api")) is None


def test_load_summary_raises_when_api_fails(monkeypatch):
    def failing_fetch(start, end):
        raise requests.ConnectionError("API down")

    monkeypatch.setattr(core.summary, "fetch_snapshots", failing_fetch)
    with pytest.raises(requests.RequestException):
        load_summary(make_config("api"))
