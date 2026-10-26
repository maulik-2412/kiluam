"""Thin FastAPI layer: validates input, caches, delegates to analysis.py."""
from datetime import date
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles

from backend import analysis

app = FastAPI(title="Wind forecast pilot")
ACTUALS, FORECASTS = analysis.load()  # loaded once at startup (small, read-only data)


@lru_cache(maxsize=32)
def _accuracy(hour: int):
    return analysis.accuracy(ACTUALS, FORECASTS, hour)


@app.get("/api/config")
def config():
    return {"days": [d.isoformat() for d in analysis.DAYS],
            "default_cutoff_hour": analysis.DEFAULT_CUTOFF_HOUR}


@app.get("/api/accuracy")
def accuracy(cutoff_hour: int = Query(analysis.DEFAULT_CUTOFF_HOUR, ge=0, le=23)):
    return _accuracy(cutoff_hour)


@app.get("/api/forecast")
def forecast(day: str, cutoff_hour: int = Query(analysis.DEFAULT_CUTOFF_HOUR, ge=0, le=23)):
    try:
        d = date.fromisoformat(day)
    except ValueError:
        raise HTTPException(400, "day must be YYYY-MM-DD")
    if d not in analysis.DAYS:
        raise HTTPException(404, "day outside the pilot window (2026-01-02 to 2026-02-01)")
    return analysis.forecast_view(ACTUALS, FORECASTS, d, cutoff_hour, _accuracy(cutoff_hour)["overall"])


# Serve the built React app (Docker / local). On Vercel the static files are served by Vercel itself.
_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")
