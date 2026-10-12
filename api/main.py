import time

import requests
from fastapi import FastAPI, HTTPException

from core.calculations import GridSummary
from core.config import load_config
from core.summary import load_summary

CACHE_SECONDS = 300  # Elexon publishes every 30 minutes, so 5 minutes is fresh enough

app = FastAPI(title="Grid greenness API")
_cache: tuple[float, GridSummary | None] | None = None  # (time loaded, summary)


def load_cached_summary() -> GridSummary | None:
    """Load the summary, reusing the last one for up to 5 minutes."""
    global _cache
    if _cache is None or time.monotonic() - _cache[0] > CACHE_SECONDS:
        _cache = (time.monotonic(), load_summary(load_config()))  # failures raise, so they aren't cached
    return _cache[1]


@app.get("/api/summary")
def get_summary() -> GridSummary | None:
    """Return the latest grid summary; 503 if the data is unavailable."""
    try:
        return load_cached_summary()
    except (requests.RequestException, OSError, ValueError, KeyError) as error:
        raise HTTPException(status_code=503, detail="Grid data is unavailable") from error
