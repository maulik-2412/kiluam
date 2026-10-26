import { useEffect, useState } from "react";
import {
  ComposedChart, Area, Line, BarChart, Bar, XAxis, YAxis, Tooltip, Legend,
  CartesianGrid, ResponsiveContainer,
} from "recharts";

const getJSON = (url) =>
  fetch(url).then((r) => (r.ok ? r.json() : Promise.reject(new Error(`${r.status} ${url}`))));
const n = (x, d = 0) => (x == null ? "–" : Number(x).toFixed(d));
const hhmm = (iso) => (iso ? iso.slice(11, 16) : "–");
const dayTime = (iso) => (iso ? `${iso.slice(0, 10)} ${iso.slice(11, 16)} UTC` : "–");

function Card({ label, value, unit }) {
  return (
    <div className="card">
      <b>{value}{unit ? ` ${unit}` : ""}</b>
      <span>{label}</span>
    </div>
  );
}

// Re-fetches whenever `url` changes; returns { data, error }
function useApi(url) {
  const [state, setState] = useState({ data: null, error: null });
  useEffect(() => {
    let live = true;
    setState({ data: null, error: null });
    getJSON(url)
      .then((data) => live && setState({ data, error: null }))
      .catch((e) => live && setState({ data: null, error: e.message }));
    return () => { live = false; };
  }, [url]);
  return state;
}

function ForecastView({ day, hour }) {
  const { data, error } = useApi(`/api/forecast?day=${day}&cutoff_hour=${hour}`);
  if (error) return <p className="err">Failed to load: {error}</p>;
  if (!data) return <p>Loading…</p>;

  const s = data.summary;
  const rows = data.points.map((p) => ({
    time: hhmm(p.t),
    Forecast: p.forecast,
    Actual: p.actual,
    band: p.low != null ? [p.low, p.high] : null,
  }));
  return (
    <>
      <div className="cards">
        <Card label="Forecast used: latest issued" value={hhmm(s.forecast_issued_latest)} unit="UTC (D-1)" />
        <Card label="Mean forecast wind" value={n(s.mean_forecast)} unit="MW" />
        <Card label="Prudent (P5) mean wind" value={n(s.mean_low_case)} unit="MW" />
        <Card label="Peak / min forecast" value={`${n(s.peak_forecast)} / ${n(s.min_forecast)}`} unit="MW" />
      </div>
      <div className="panel">
        <ResponsiveContainer width="100%" height={340}>
          <ComposedChart data={rows}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="time" interval={5} />
            <YAxis unit=" MW" width={80} />
            <Tooltip />
            <Legend />
            <Area dataKey="band" name="Typical error range (P5–P95)" fill="#9fc5e8" stroke="none" fillOpacity={0.5} />
            <Line dataKey="Forecast" stroke="#1565c0" dot={false} strokeWidth={2} />
            <Line dataKey="Actual" stroke="#e65100" dot={false} strokeWidth={2} />
          </ComposedChart>
        </ResponsiveContainer>
        <p className="note">
          Decision point: {dayTime(data.cutoff)}. For each hour we show the latest forecast published
          at or before that time (issued {dayTime(s.forecast_issued_earliest)} – {dayTime(s.forecast_issued_latest)}).
          The shaded band is the forecast plus the 5th–95th percentile of historical error (actual − forecast) over the whole pilot month.
          Forecast available for {s.periods_with_forecast}/24 periods, actuals for {s.periods_with_actual}/24.
        </p>
      </div>
    </>
  );
}

function AccuracyView({ hour }) {
  const { data, error } = useApi(`/api/accuracy?cutoff_hour=${hour}`);
  if (error) return <p className="err">Failed to load: {error}</p>;
  if (!data) return <p>Loading…</p>;
  const o = data.overall;
  const daily = data.daily.map((d) => ({ day: d.day.slice(5), MAE: d.mae, RMSE: d.rmse }));
  return (
    <>
      <div className="cards">
        <Card label="Mean absolute error (MAE)" value={n(o.mae)} unit="MW" />
        <Card label="RMSE" value={n(o.rmse)} unit="MW" />
        <Card label="Bias (actual − forecast)" value={n(o.bias)} unit="MW" />
        <Card label="MAE as % of mean actual" value={n(o.rel_mae_pct, 1)} unit="%" />
        <Card label="P5 error (wind below forecast)" value={n(o.p5)} unit="MW" />
        <Card label="P95 error (wind above forecast)" value={n(o.p95)} unit="MW" />
      </div>
      <div className="panel">
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={daily}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="day" interval={2} />
            <YAxis unit=" MW" width={80} />
            <Tooltip formatter={(v) => `${n(v)} MW`} />
            <Legend />
            <Bar dataKey="MAE" fill="#1565c0" />
            <Bar dataKey="RMSE" fill="#90a4ae" />
          </BarChart>
        </ResponsiveContainer>
        <p className="note">
          Daily error by delivery day (MM-DD), using only forecasts available at the decision point. {o.n} hourly
          periods compared. Error percentiles are in-sample (computed on the same month they describe).
        </p>
      </div>
    </>
  );
}

export default function App() {
  const [cfg, setCfg] = useState(null);
  const [failed, setFailed] = useState(null);
  const [tab, setTab] = useState("forecast");
  const [day, setDay] = useState("");
  const [hour, setHour] = useState(9);

  useEffect(() => {
    getJSON("/api/config")
      .then((c) => { setCfg(c); setDay(c.days[0]); setHour(c.default_cutoff_hour); })
      .catch((e) => setFailed(e.message));
  }, []);

  if (failed) return <main><p className="err">Cannot reach the API: {failed}</p></main>;
  if (!cfg) return <main><p>Loading…</p></main>;

  return (
    <main>
      <h1>UK day-ahead wind forecast pilot</h1>
      <p className="sub">National wind generation, Elexon data (FUELHH actuals, WINDFOR forecasts). Decisions made in January 2026.</p>
      <div className="bar">
        <button className={tab === "forecast" ? "on" : ""} onClick={() => setTab("forecast")}>Day-ahead forecast</button>
        <button className={tab === "accuracy" ? "on" : ""} onClick={() => setTab("accuracy")}>Forecast accuracy</button>
        <label>Decision time (D-1, UTC){" "}
          <select value={hour} onChange={(e) => setHour(Number(e.target.value))}>
            {[6, 7, 8, 9, 10, 11, 12].map((h) => <option key={h} value={h}>{String(h).padStart(2, "0")}:00</option>)}
          </select>
        </label>
        {tab === "forecast" && (
          <label>Delivery day{" "}
            <select value={day} onChange={(e) => setDay(e.target.value)}>
              {cfg.days.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </label>
        )}
      </div>
      {tab === "forecast" ? <ForecastView day={day} hour={hour} /> : <AccuracyView hour={hour} />}
    </main>
  );
}
