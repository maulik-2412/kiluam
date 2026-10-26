"""Download the data for the pilot window from Elexon into backend/data/*.csv.

Run once (needs internet, no API key):  python scripts/fetch_data.py
Stdlib only. Output is committed so the app never depends on Elexon being up.

Window: purchase decisions made 1-31 Jan 2026  ->  delivery days 2 Jan - 1 Feb 2026.
"""
import csv
import json
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = "https://data.elexon.co.uk/bmrs/api/v1/datasets"
UTC = timezone.utc
OUT = Path(__file__).resolve().parent.parent / "backend" / "data"

DELIVERY_START = datetime(2026, 1, 2, tzinfo=UTC)
DELIVERY_END = datetime(2026, 2, 2, tzinfo=UTC)      # exclusive
PUBLISH_START = datetime(2026, 1, 1, tzinfo=UTC)
PUBLISH_END = datetime(2026, 2, 1, tzinfo=UTC)       # exclusive
MAX_HORIZON = timedelta(hours=48)                    # a day-ahead decision never needs more


def get(dataset, **params):
    url = f"{BASE}/{dataset}/stream?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        data = json.load(r)
    return data if isinstance(data, list) else data.get("data", [])


def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_actuals():
    rows = {}
    day = DELIVERY_START
    while day < DELIVERY_END:
        end = min(day + timedelta(days=5), DELIVERY_END) - timedelta(days=1)
        print(f"FUELHH {day:%Y-%m-%d} -> {end:%Y-%m-%d}")
        for r in get("FUELHH", settlementDateFrom=f"{day:%Y-%m-%d}",
                     settlementDateTo=f"{end:%Y-%m-%d}", fuelType="WIND"):
            if r.get("fuelType") == "WIND" and r.get("generation") is not None:
                rows[iso(ts(r["startTime"]))] = r["generation"]
        day += timedelta(days=5)
    return rows


def fetch_forecasts():
    rows = set()
    day = PUBLISH_START
    while day < PUBLISH_END:
        nxt = day + timedelta(days=1)
        print(f"WINDFOR published {day:%Y-%m-%d}")
        for r in get("WINDFOR", publishDateTimeFrom=iso(day), publishDateTimeTo=iso(nxt)):
            if r.get("generation") is None:
                continue
            start, pub = ts(r["startTime"]), ts(r["publishTime"])
            if DELIVERY_START <= start < DELIVERY_END and timedelta(0) <= start - pub <= MAX_HORIZON:
                rows.add((iso(start), iso(pub), r["generation"]))
        day = nxt
    return sorted(rows)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    actuals = fetch_actuals()
    with open(OUT / "actuals.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["startTime", "generation"])
        w.writerows(sorted(actuals.items()))
    forecasts = fetch_forecasts()
    with open(OUT / "forecasts.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["startTime", "publishTime", "generation"])
        w.writerows(forecasts)
    print(f"Done: {len(actuals)} actual rows, {len(forecasts)} forecast rows -> {OUT}")
