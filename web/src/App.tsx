import { useEffect, useState } from "react";

import { Anomalies } from "./components/Anomalies";
import { Cohorts } from "./components/Cohorts";
import { Footer } from "./components/Footer";
import { Forecast } from "./components/Forecast";
import { Integrity } from "./components/Integrity";
import { Summary } from "./components/Summary";
import { loadAll } from "./data";
import type { AppData } from "./types";

export default function App() {
  const [data, setData] = useState<AppData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [title, setTitle] = useState<string>("PLAYERUNKNOWN'S BATTLEGROUNDS");

  useEffect(() => {
    loadAll().then(setData).catch((e: Error) => setError(e.message));
  }, []);

  if (error) return <div className="state"><p>{error}</p></div>;
  if (!data) return <div className="state"><p className="mono">Loading Pulse…</p></div>;

  const s = data.integrity.summary;

  return (
    <>
      <header className="hero">
        <div className="wrap">
          <p className="eyebrow">Engagement analytics · live-service games</p>
          <h1>
            Pulse<span>.</span>
          </h1>
          <p className="lead">
            A live-service engagement monitor built on {s.rows.toLocaleString()} real hourly readings of the 100 most
            played games on Steam. It audits the data first, then forecasts, flags anomalies, and compares launches,
            with every number traceable to the SQL that produced it.
          </p>
          <div className="badges">
            <span className="badge real">Real data, not simulated</span>
            <span className="badge">{data.meta.dataset.license}</span>
            <span className="badge">May 2018 to Mar 2019</span>
            <span className="badge">{s.titles} titles</span>
            <span className="badge">Python + DuckDB + React</span>
          </div>
        </div>
      </header>

      <nav className="picker" aria-label="Choose a title">
        <div className="wrap">
          <span className="picker-label">Title</span>
          {data.meta.titles.map((t) => (
            <button key={t.title} type="button" className="pill" aria-pressed={t.title === title} onClick={() => setTitle(t.title)}>
              {t.name}
            </button>
          ))}
        </div>
      </nav>

      <main>
        <Summary data={data} title={title} />
        <Integrity data={data} />
        <Forecast data={data} title={title} />
        <Anomalies data={data} title={title} />
        <Cohorts data={data} />
        <Footer data={data} />
      </main>
    </>
  );
}
