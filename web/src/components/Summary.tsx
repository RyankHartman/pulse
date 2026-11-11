import { pct } from "../format";
import type { AppData } from "../types";

export function Summary({ data, title }: { data: AppData; title: string }) {
  const summary = data.summary.titles[title];
  const forecast = data.forecast.titles[title];
  const anomalies = data.anomalies.titles[title];
  if (!summary || !forecast || !anomalies) return null;

  const { test } = forecast.backtest;
  const coverageOk = Math.abs(test.coverage80 - 0.8) <= 0.07;
  const trend = forecast.trend.change_pct;

  return (
    <section className="block" id="summary">
      <div className="wrap">
        <header>
          <p className="eyebrow">Executive summary · {summary.name}</p>
          <h2>What a leader needs to know, in one screen.</h2>
          <p className="lead">
            Every sentence below is generated from a number the pipeline computed, so nothing is invented and it
            changes whenever you pick a different title.
          </p>
        </header>

        <p className="headline">{summary.headline}</p>

        <div className="grid g4" style={{ marginTop: "1.6rem" }}>
          <div className={`kpi ${trend >= 0 ? "good" : "warn"}`}>
            <p className="label">Daily peak, window change</p>
            <p className="value">{`${trend >= 0 ? "+" : ""}${trend.toFixed(0)}%`}</p>
            <p className="note">first 4 weeks vs last 4</p>
          </div>
          <div className={`kpi ${test.skill_vs_naive >= 0 ? "good" : "warn"}`}>
            <p className="label">14-day forecast error</p>
            <p className="value">{pct(test.mape, 1)}</p>
            <p className="note">baseline: {pct(test.naive_mape, 1)}</p>
          </div>
          <div className={`kpi ${coverageOk ? "good" : "warn"}`}>
            <p className="label">80% band actually held</p>
            <p className="value">{pct(test.coverage80)}</p>
            <p className="note">target 80%, {test.days_scored} days scored</p>
          </div>
          <div className="kpi">
            <p className="label">Anomalies flagged</p>
            <p className="value">{anomalies.events.length}</p>
            <p className="note">{anomalies.counts.title_specific} title-specific</p>
          </div>
        </div>

        <ul className="bullets">
          {summary.bullets.map((bullet) => (
            <li key={bullet.label}>
              <span className="tag">{bullet.label}</span>
              <p>{bullet.text}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
