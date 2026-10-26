# UK day-ahead wind forecast pilot

A small web app for a UK utility's day-ahead power buying team. It answers two questions about **national wind generation** (Elexon data only):

1. **What is the latest wind forecast I can actually use when I make tomorrow's purchase decision?**
2. **How accurate has that forecast been, in MW, so I can allow for the error?**

**Live app:** _<add Vercel/Heroku link here>_

> **AI disclosure:** this project was built with the help of Claude (Anthropic) for design, code and documentation. I reviewed, ran and tested the code.

## How to start

**1. Get the data (once, needs internet, no API key).** The pilot window is fixed, so data is downloaded once and committed to the repo. The app never calls Elexon at runtime.

```bash
python scripts/fetch_data.py        # writes backend/data/actuals.csv and forecasts.csv
```

**2a. Docker (one container serves API + built React app):**

```bash
docker build -t wind-pilot .
docker run -p 8000:8000 wind-pilot   # open http://localhost:8000
```

**2b. Local dev (two terminals):**

```bash
pip install -r requirements.txt
uvicorn backend.app:app --reload --port 8000

cd frontend && npm install && npm run dev      # http://localhost:5173 (proxies /api to :8000)
```

**Tests:** `python -m unittest discover` (standard library only).

**Deploy (Vercel):** import the repo; `vercel.json` builds the React app and exposes `api/index.py` (FastAPI) as the backend. Deployed Docker-style on Heroku/Render/Fly the same `Dockerfile` works (reads `$PORT`).

## Files and directories

| Path | What it is |
|---|---|
| `backend/analysis.py` | All the logic: load data, pick the decision-time forecast, compute error metrics. Pure Python, no framework. |
| `backend/app.py` | FastAPI: 3 endpoints, input validation, caching; serves the built React app when present. |
| `backend/data/` | `actuals.csv`, `forecasts.csv` created by the fetch script. |
| `scripts/fetch_data.py` | One-off download from Elexon FUELHH (WIND) and WINDFOR. Standard library only. |
| `frontend/src/App.jsx` | The whole UI: two tabs (forecast, accuracy) and two charts. |
| `tests/test_analysis.py` | Unit tests for the core rules. |
| `api/index.py` | 1-line Vercel entrypoint that exposes the FastAPI app. |
| `Dockerfile` | Multi-stage: build React, then run Python serving everything. |
| `vercel.json` | Vercel build + routing config. |
| `VIDEO_SCRIPT.md` | Script for the 2-part demo video. |

## API

- `GET /api/config`: delivery days available and default decision hour.
- `GET /api/forecast?day=YYYY-MM-DD&cutoff_hour=9`: 48 half-hourly points (forecast, actual, error band) plus a summary.
- `GET /api/accuracy?cutoff_hour=9`: overall and per-day MAE, RMSE, bias, relative MAE, P5/P95 error.

## Design decisions (and why)

- **"Latest forecast available at decision time"** is the core rule. For delivery day D, the buyer decides on D-1 at a cutoff hour; for each half-hour we use the forecast with the latest `publishTime` at or before that cutoff. Accuracy is measured on exactly this forecast, not on the freshest forecast, which would flatter the numbers because the buyer could never have used it.
- **Window:** "decisions made in January 2026" means delivery days **2 Jan to 1 Feb 2026**. Forecasts published 1-31 Jan are fetched, restricted to horizons of up to 48 h.
- **Decision time is an assumption:** default **09:00 UTC on D-1**, selectable 06:00-12:00 in the UI. I chose a time before the usual day-ahead auction gate closures; the real trading desk's cutoff should replace it. GB is on GMT in January, so UTC equals local time and there is no daylight-saving handling.
- **Error definition:** error = actual − forecast, so negative means wind under-delivered (the costly case for a buyer). Metrics: MAE, RMSE, bias, MAE as % of mean actual (used instead of MAPE, which breaks near zero wind). The P5/P95 error percentiles drive the shaded band on the chart, so the quantified error feeds directly into the decision.
- **Snapshot data instead of live API calls:** January 2026 is fixed history. A CSV snapshot makes the app fast, free of an external dependency, and easy to deploy (no database, no secrets).
- **No pandas, no database, no auth:** ~100k rows fit in memory; the standard library is enough. This keeps the Vercel bundle small and the code easy to read.
- **One analysis module, thin API, one-file UI:** logic is testable without a server; the API only validates and caches.

## Known limitations

- Wind forecast only: no demand data, so the app does not compute the amount to buy; the buyer subtracts the forecast from their own demand view.
- Error percentiles are **in-sample** (computed on the same month), so the band for an early-January day uses information from later in the month. Fine for a pilot; production should use a rolling window of past days.
- One national aggregate; no regional or time-of-day error breakdown.
- A month is a small sample for tail percentiles such as P5/P95.
