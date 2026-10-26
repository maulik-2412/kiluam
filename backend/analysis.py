"""Pure analysis logic. No web framework, no pandas: just the standard library.

Key idea: for a delivery day D, the buyer decides on day D-1 at a cutoff hour
(default 09:00). For every half-hour of D the forecast they can use is the
latest one published at or before that cutoff. We compare it with the actual.

GB is on GMT (= UTC) in January, so there is no DST handling anywhere.
"""
import bisect
import csv
import math
import os
import statistics
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

UTC = timezone.utc
DATA_DIR = Path(os.environ.get("WIND_DATA_DIR", Path(__file__).parent / "data"))

# Decisions are made 1-31 Jan 2026, so delivery days are 2 Jan - 1 Feb 2026.
DAYS = [date(2026, 1, 2) + timedelta(days=i) for i in range(31)]
DEFAULT_CUTOFF_HOUR = 9  # assumption, see README


def _ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _iso(dt):
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def load():
    """Return (actuals, forecasts).
    actuals:   {startTime: MW}
    forecasts: {startTime: [(publishTime, MW), ...] sorted by publishTime}
    """
    try:
        actuals, forecasts = {}, {}
        with open(DATA_DIR / "actuals.csv") as f:
            for r in csv.DictReader(f):
                actuals[_ts(r["startTime"])] = float(r["generation"])
        with open(DATA_DIR / "forecasts.csv") as f:
            for r in csv.DictReader(f):
                forecasts.setdefault(_ts(r["startTime"]), []).append(
                    (_ts(r["publishTime"]), float(r["generation"])))
    except FileNotFoundError as e:
        raise FileNotFoundError(f"{e}. Run `python scripts/fetch_data.py` first.") from e
    for rows in forecasts.values():
        rows.sort()
    return actuals, forecasts


def decision_forecast(forecasts, t, cutoff):
    """Latest (publishTime, MW) for target time t published at or before cutoff."""
    rows = forecasts.get(t, [])
    i = bisect.bisect_right(rows, (cutoff, math.inf))
    return rows[i - 1] if i else None

def _hourly_actual(actuals, hour_start):
    """Average the two half-hourly actual readings for one complete hour."""
    first = actuals.get(hour_start)
    second = actuals.get(hour_start + timedelta(minutes=30))

    # Require both readings so incomplete hours do not distort metrics.
    if first is None or second is None:
        return None

    return (first + second) / 2

def day_series(actuals, forecasts, day, cutoff_hour):
    """24 hourly points for a delivery day, using the decision-time forecast."""
    cutoff = datetime(day.year, day.month, day.day, cutoff_hour, tzinfo=UTC) - timedelta(days=1)
    start = datetime(day.year, day.month, day.day, tzinfo=UTC)
    points = []
    for k in range(24):
        t = start + timedelta(hours=k)
        f = decision_forecast(forecasts, t, cutoff)
        points.append({
            "t": _iso(t),
            "actual": _hourly_actual(actuals, t),
            "forecast": f[1] if f else None,
            "published": _iso(f[0]) if f else None,
        })
    return points


def metrics(pairs):
    """pairs = [(actual, forecast)]. Error = actual - forecast (negative = wind under-delivered)."""
    if not pairs:
        return {"n": 0}
    errs = [a - f for a, f in pairs]
    mean_actual = statistics.fmean(a for a, _ in pairs)
    mae = statistics.fmean(abs(e) for e in errs)
    out = {
        "n": len(errs),
        "mae": mae,
        "rmse": math.sqrt(statistics.fmean(e * e for e in errs)),
        "bias": statistics.fmean(errs),
        "mean_actual": mean_actual,
        "rel_mae_pct": mae / mean_actual * 100 if mean_actual else None,
    }
    if len(errs) >= 2:
        q = statistics.quantiles(errs, n=20, method="inclusive")
        out["p5"], out["p95"] = q[0], q[18]
    return out


def accuracy(actuals, forecasts, cutoff_hour):
    daily, all_pairs = [], []
    for d in DAYS:
        pts = day_series(actuals, forecasts, d, cutoff_hour)
        pairs = [(p["actual"], p["forecast"]) for p in pts
                 if p["actual"] is not None and p["forecast"] is not None]
        all_pairs += pairs
        daily.append({"day": d.isoformat(), **metrics(pairs)})
    return {"cutoff_hour": cutoff_hour, "overall": metrics(all_pairs), "daily": daily}


def forecast_view(actuals, forecasts, day, cutoff_hour, overall):
    """Day series plus an error band (forecast + P5 / P95 historical error) and a summary."""
    pts = day_series(actuals, forecasts, day, cutoff_hour)
    p5, p95 = overall.get("p5"), overall.get("p95")
    for p in pts:
        f = p["forecast"]
        p["low"] = max(0.0, f + p5) if f is not None and p5 is not None else None
        p["high"] = f + p95 if f is not None and p95 is not None else None
    fv = [p["forecast"] for p in pts if p["forecast"] is not None]
    lows = [p["low"] for p in pts if p["low"] is not None]
    pub = [p["published"] for p in pts if p["published"]]
    summary = {
        "periods_with_forecast": len(fv),
        "periods_with_actual": sum(p["actual"] is not None for p in pts),
        "mean_forecast": statistics.fmean(fv) if fv else None,
        "peak_forecast": max(fv) if fv else None,
        "min_forecast": min(fv) if fv else None,
        "mean_low_case": statistics.fmean(lows) if lows else None,
        "forecast_issued_latest": max(pub) if pub else None,
        "forecast_issued_earliest": min(pub) if pub else None,
    }
    cutoff = datetime(day.year, day.month, day.day, cutoff_hour, tzinfo=UTC) - timedelta(days=1)
    return {"day": day.isoformat(), "cutoff": _iso(cutoff), "points": pts, "summary": summary,
            "error_band": {"p5": p5, "p95": p95}}
