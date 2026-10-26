# Video script (max 10 min total, upload as unlisted YouTube)

**Before recording:** run the fetch script, open the live app, and fill the `[X]` placeholders with the real numbers from the Accuracy tab. Pick one interesting delivery day (a windy day with a big miss works well) and one calm day. Keep browser zoom at ~125% so text is readable.

---

## PART 1: Client pitch (about 4:30)

**[0:00-0:30] The problem. Screen: title slide or app landing page**
> "Every morning your team buys tomorrow's power in the day-ahead market. The less wind we expect, the more you have to buy from thermal plants. But wind is weather-dependent, and you must commit the day before. So two questions matter: what is the latest wind forecast I can really rely on at decision time, and how wrong has that forecast been in the past?"

**[0:30-1:00] What we built. Screen: app, Day-ahead forecast tab**
> "We built a portal that answers exactly those two questions, using national wind data from Elexon: actual generation and the published forecasts. This pilot covers every decision made in January 2026, so delivery days from 2 January to 1 February."

**[1:00-2:30] Feature 1: the forecast you can actually use. Screen: Forecast tab, pick a delivery day**
> "Pick a delivery day. The blue line is the forecast available at your decision time, here 09:00 the day before. Notice the cards: it shows when that forecast was issued, the average wind we expect, and the peak and minimum."
> "The shaded band is the typical error range, the 5th to 95th percentile of past mistakes. Orange is what really happened. So you see the forecast and how far reality has historically strayed from it."
> "The 'prudent' card shows average wind if the forecast under-delivers by a typical bad amount. That is the number to plan your thermal purchase buffer around: 12996 MW lower on average than the headline forecast."
Show: change decision time from 09:00 to 11:00 and point out the forecast changes because a newer one is picked.

**[2:30-3:45] Feature 2: measured accuracy. Screen: Forecast accuracy tab**
> "Across the month, the forecast was off by 2039 MW on average, which is 18.1 percent of average wind output. The bias is -1748 MW, so it tends to over-predict. In the worst 5 percent of hours, wind came in 5283 MW below forecast, and that is the risk you are hedging."
> "The daily chart shows error is not constant: it was largest on 01-28, when 5375, and smallest on 01-19. That tells your team which days to trust less."

**[3:45-4:30] Value and next steps. Screen: Accuracy tab or closing slide**
> "What does this give you? A decision-time-correct forecast, error in MW instead of a vague 'it's usually fine', and a view that takes seconds to read. Next steps: add your demand view so the app outputs the volume to buy, extend to solar and regional data, and size the buffer from rolling error history. Happy to take questions."

---

## PART 2: Tech lead review (about 5:00)

**[4:30-5:30] Architecture. Screen: README file table or a simple diagram**
> "Three pieces. One: a fetch script that pulls Elexon FUELHH (filtered to WIND) and WINDFOR once and saves two CSVs. Two: a FastAPI backend with all logic in `analysis.py` and three thin endpoints. Three: a React single-page app with two charts. One Docker image serves both API and built UI; on Vercel the same code runs as a static site plus a serverless function."
> "I deliberately chose a data snapshot over live API calls: January 2026 is fixed history, so it is faster, has no runtime dependency, and needs no database."

**[5:30-7:00] The core logic. Screen: `backend/analysis.py`**
> "The key function is `decision_forecast`. For a target half-hour and a cutoff time, it binary-searches that target's forecasts, sorted by publish time, and returns the latest one at or before the cutoff. Everything else builds on it."
> "`day_series` builds 24 points for a delivery day. `metrics` computes MAE, RMSE, bias, relative MAE and the P5/P95 error. Error is actual minus forecast, so negative means under-delivery."
> "Why this matters: if I scored the freshest forecast instead, accuracy would look better than anything the buyer could use. That is the main analytical trap in this problem."

**[7:00-7:45] API and frontend. Screen: `backend/app.py`, then `frontend/src/App.jsx`**
> "`app.py` validates input, caches the accuracy result per cutoff hour, and delegates. The UI is one file: a small `useApi` hook, a Forecast view and an Accuracy view. The band is a Recharts range area using the P5/P95 from the accuracy endpoint."

**[7:45-8:30] Practices and data pipeline. Screen: `tests/`, `scripts/fetch_data.py`, Dockerfile**
> "Standard library only for the backend, so the Vercel bundle stays small. Unit tests cover the cutoff rule, the metrics and missing data; run them with `python -m unittest`. The fetch script chunks requests, dedupes, filters to WIND, and limits forecast horizon to 48 hours. The Dockerfile is multi-stage. AI assistance is disclosed in the README."

**[8:30-9:30] Assumptions and limitations. Screen: README, Known limitations**
> "Assumptions to flag: the 09:00 D-1 decision time is mine and is a dropdown, and 'decisions in January' means delivery 2 Jan to 1 Feb. Limitations: the error percentiles are in-sample, so production should use a rolling past-days window; there is no demand data; and one month is a small sample for tail percentiles. Next I would add a rolling-error window, error by horizon and time of day, and a scheduled data refresh. Also we couldn't do half-hourly graphs as we have half-hourly data for actuals, but forecasts are only hourly."

**[9:30-10:00] Close**
> "Everything is in the repo with a README explaining the files and how to run it. Thank you."
