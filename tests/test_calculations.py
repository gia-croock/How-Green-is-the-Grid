from datetime import UTC, datetime
from pathlib import Path

import pytest

from core.calculations import (
    clip_negatives,
    average_not_green_percent,
    format_period,
    get_baseline,
    is_above_baseline,
    summarise_grid,
    sum_by_rating,
    to_percentages,
    to_uk_time,
)
from core.config import load_config
from core.data import Snapshot, load_snapshot

SAMPLE = Path("data/sample.json")
SAMPLE_TOTALS = {"green": 15402, "not_green": 1960, "neutral": 2693}


def make_snapshot(generation: dict[str, float], start: datetime) -> Snapshot:
    return Snapshot(start_time=start, settlement_period=1, generation=generation)


# --- calculation rules ---

def test_clip_negatives_replaces_negatives_with_zero():
    assert clip_negatives({"A": 5, "B": -3, "C": 0}) == {"A": 5, "B": 0, "C": 0}


def test_sum_by_rating_on_sample():
    config = load_config()
    generation = clip_negatives(load_snapshot(SAMPLE).generation)
    assert sum_by_rating(generation, config["fuel_ratings"]) == SAMPLE_TOTALS


def test_unrated_fuel_counts_as_neutral_and_is_logged(caplog):
    totals = sum_by_rating({"WIND": 10, "NEWFUEL": 5}, {"WIND": "green"})
    assert totals == {"green": 10, "not_green": 0, "neutral": 5}
    assert "NEWFUEL" in caplog.text


def test_to_percentages_on_sample():
    percentages = to_percentages(SAMPLE_TOTALS)
    assert percentages["green"] == pytest.approx(76.8, abs=0.05)
    assert percentages["not_green"] == pytest.approx(9.8, abs=0.05)
    assert percentages["neutral"] == pytest.approx(13.4, abs=0.05)
    assert sum(percentages.values()) == pytest.approx(100)


def test_to_percentages_returns_none_when_total_is_zero():
    assert to_percentages({"green": 0, "not_green": 0, "neutral": 0}) is None


# --- "higher than normal" ---

@pytest.mark.parametrize(
    "not_green, expected",
    [(27.1, True), (27.0, False), (10.0, False)],  # strictly above only
)
def test_is_above_baseline(not_green, expected):
    assert is_above_baseline(not_green, 27.0) is expected


# --- time ---

def test_to_uk_time_uses_bst_in_summer():
    uk = to_uk_time(datetime(2025, 3, 30, 12, 0, tzinfo=UTC))
    assert (uk.hour, uk.tzname()) == (13, "BST")


def test_to_uk_time_uses_gmt_in_winter():
    uk = to_uk_time(datetime(2025, 1, 15, 12, 0, tzinfo=UTC))
    assert (uk.hour, uk.tzname()) == (12, "GMT")


def uk(*utc_parts: int) -> datetime:
    return to_uk_time(datetime(*utc_parts, tzinfo=UTC))


def test_format_period_normal():
    assert format_period(uk(2025, 3, 30, 12, 0), uk(2025, 3, 30, 12, 30)) == "30 Mar 2025, 13:00-13:30 BST"


def test_format_period_clocks_forward():
    assert format_period(uk(2025, 3, 30, 0, 30), uk(2025, 3, 30, 1, 0)) == "30 Mar 2025, 00:30 GMT-02:00 BST"


def test_format_period_clocks_back():
    assert format_period(uk(2025, 10, 26, 0, 30), uk(2025, 10, 26, 1, 0)) == "26 Oct 2025, 01:30 BST-01:00 GMT"


# --- full summary ---

def test_summarise_grid_on_sample():
    summary = summarise_grid(load_snapshot(SAMPLE), load_config())
    assert summary.percentages["green"] == pytest.approx(76.8, abs=0.05)
    assert summary.baseline_percent == 27
    assert summary.above_baseline is False
    assert (summary.period_start.hour, summary.period_start.minute) == (13, 0)
    assert (summary.period_end.hour, summary.period_end.minute) == (13, 30)
    assert summary.period_label == "30 Mar 2025, 13:00-13:30 BST"


def test_summarise_grid_flags_high_not_green():
    snapshot = make_snapshot({"CCGT": 40, "WIND": 60}, datetime(2025, 1, 15, 18, 0, tzinfo=UTC))
    assert summarise_grid(snapshot, load_config()).above_baseline is True


def test_summarise_grid_period_end_across_clock_change():
    # 00:30 GMT + 30 min = 01:00 GMT, which the clocks show as 02:00 BST
    snapshot = make_snapshot({"WIND": 100}, datetime(2025, 3, 30, 0, 30, tzinfo=UTC))
    summary = summarise_grid(snapshot, load_config())
    assert (summary.period_start.hour, summary.period_start.tzname()) == (0, "GMT")
    assert (summary.period_end.hour, summary.period_end.tzname()) == (2, "BST")


def test_summarise_grid_returns_none_when_no_generation():
    snapshot = make_snapshot({"PS": -500, "INTFR": -200}, datetime(2025, 1, 15, 12, 0, tzinfo=UTC))
    assert summarise_grid(snapshot, load_config()) is None


# --- dynamic baseline ---

RATINGS = {"CCGT": "not_green", "WIND": "green"}
HISTORY = [  # three consecutive half-hours
    make_snapshot({"CCGT": 100, "WIND": 900}, datetime(2025, 1, 15, 11, 0, tzinfo=UTC)),  # 10% not green, 1,000 MW
    make_snapshot({"CCGT": 600, "WIND": 1400}, datetime(2025, 1, 15, 11, 30, tzinfo=UTC)),  # 30% not green, 2,000 MW
    make_snapshot({"CCGT": -5}, datetime(2025, 1, 15, 12, 0, tzinfo=UTC)),  # no generation: skipped
]


def make_config(mode: str) -> dict:
    return {"baseline": {"mode": mode, "static_percent": 27}, "fuel_ratings": RATINGS}


def test_average_not_green_percent_is_unweighted():
    # Each half-hour counts equally: (10 + 30) / 2 = 20, not 700 / 3,000 = 23.3
    assert average_not_green_percent(HISTORY, RATINGS) == pytest.approx(20)


def test_get_baseline_dynamic_uses_history():
    assert get_baseline(make_config("dynamic"), HISTORY) == pytest.approx(20)


def test_get_baseline_falls_back_to_static():
    assert get_baseline(make_config("dynamic"), []) == 27  # no history
    assert get_baseline(make_config("static"), HISTORY) == 27  # static mode
