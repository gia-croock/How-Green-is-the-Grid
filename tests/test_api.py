from pathlib import Path

import pytest
import requests
from fastapi.testclient import TestClient

import api.main
from core.calculations import summarise_grid
from core.config import load_config
from core.data import load_snapshot

SAMPLE_SUMMARY = summarise_grid(load_snapshot(Path("data/sample.json")), load_config())
client = TestClient(api.main.app)


@pytest.fixture(autouse=True)
def empty_cache(monkeypatch):
    # Each test starts with nothing cached.
    monkeypatch.setattr(api.main, "_cache", None)


def test_summary_returns_json(monkeypatch):
    monkeypatch.setattr(api.main, "load_summary", lambda config: SAMPLE_SUMMARY)
    response = client.get("/api/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["percentages"]["green"] == pytest.approx(76.8, abs=0.05)
    assert body["above_baseline"] is False
    assert body["period_label"] == "30 Mar 2025, 13:00-13:30 BST"


def test_summary_returns_null_when_no_data(monkeypatch):
    monkeypatch.setattr(api.main, "load_summary", lambda config: None)
    response = client.get("/api/summary")
    assert response.status_code == 200
    assert response.json() is None


def test_summary_returns_503_when_elexon_fails(monkeypatch):
    def failing_load(config):
        raise requests.ConnectionError("Elexon down")

    monkeypatch.setattr(api.main, "load_summary", failing_load)
    response = client.get("/api/summary")
    assert response.status_code == 503
    assert response.json() == {"detail": "Grid data is unavailable"}

