import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from core.data import Snapshot

logger = logging.getLogger(__name__)

UK = ZoneInfo("Europe/London")
RATINGS = ("green", "not_green", "neutral")
PERIOD = timedelta(minutes=30)


@dataclass
class GridSummary:
    """Everything the UI needs to display one half-hour."""

    period_start: datetime  # UK local time
    period_end: datetime  # UK local time
    period_label: str  # e.g. "30 Mar 2025, 13:00-13:30 BST"
    percentages: dict[str, float]  # % by rating: green, neutral, not_green
    baseline_percent: float  # Not green % considered normal
    above_baseline: bool  # result of is_above_baseline


def clip_negatives(generation: dict[str, float]) -> dict[str, float]:
    """Replace negative MW values with 0."""
    return {fuel: max(mw, 0) for fuel, mw in generation.items()}


def sum_by_rating(generation: dict[str, float], ratings: dict[str, str]) -> dict[str, float]:
    """Total MW per rating; unrated fuel types count as neutral and are logged."""
    totals = dict.fromkeys(RATINGS, 0.0)
    for fuel, mw in generation.items():
        if fuel not in ratings:
            logger.warning("Unrated fuel type %s counted as neutral", fuel)
        totals[ratings.get(fuel, "neutral")] += mw
    return totals


def to_percentages(totals: dict[str, float]) -> dict[str, float] | None:
    """Convert MW totals to percentages of the overall total; None if the total is 0."""
    total = sum(totals.values())
    if total == 0:
        return None
    return {rating: mw / total * 100 for rating, mw in totals.items()}


def is_above_baseline(not_green_percent: float, baseline_percent: float) -> bool:
    """Return True if the Not green % is strictly above the baseline."""
    return not_green_percent > baseline_percent


def to_uk_time(utc_time: datetime) -> datetime:
    """Convert a UTC datetime to UK local time (GMT or BST)."""
    return utc_time.astimezone(UK)


def format_period(start: datetime, end: datetime) -> str:
    """Format a UK-local period, showing both time zones when a clock change splits it."""
    start_zone = f" {start:%Z}" if start.tzname() != end.tzname() else ""
    return f"{start:%d %b %Y, %H:%M}{start_zone}-{end:%H:%M %Z}"


def average_not_green_percent(history: Sequence[Snapshot], ratings: dict[str, str]) -> float | None:
    """Plain average Not green % across half-hours; None if none have generation."""
    all_percentages = [to_percentages(sum_by_rating(clip_negatives(s.generation), ratings)) for s in history]
    not_green = [percentages["not_green"] for percentages in all_percentages if percentages is not None]
    return sum(not_green) / len(not_green) if not_green else None


def get_baseline(config: dict[str, Any], history: Sequence[Snapshot]) -> float:
    """Return the dynamic baseline if configured and available, else the static one."""
    static = config["baseline"]["static_percent"]
    if config["baseline"]["mode"] != "dynamic":
        return static
    average = average_not_green_percent(history, config["fuel_ratings"])
    return static if average is None else average


def summarise_grid(
    snapshot: Snapshot, config: dict[str, Any], history: Sequence[Snapshot] = ()
) -> GridSummary | None:
    """Build the display summary for a snapshot; None if there is no generation."""
    totals = sum_by_rating(clip_negatives(snapshot.generation), config["fuel_ratings"])
    percentages = to_percentages(totals)
    if percentages is None:
        return None
    baseline = get_baseline(config, history)
    start = to_uk_time(snapshot.start_time)
    end = to_uk_time(snapshot.start_time + PERIOD)  # add in UTC, then convert
    return GridSummary(
        period_start=start,
        period_end=end,
        period_label=format_period(start, end),
        percentages=percentages,
        baseline_percent=baseline,
        above_baseline=is_above_baseline(percentages["not_green"], baseline),
    )
