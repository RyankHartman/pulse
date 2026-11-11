import { useMemo, useState } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { compact, longDate, pct, shortDate } from "../format";
import type { AppData, ForecastRow } from "../types";
import { SqlViewer } from "./SqlViewer";

type Mode = "holdout" | "projection";

interface Point {
  day: string;
  actual?: number | null;
  mid?: number;
  band80?: [number, number];
  band95?: [number, number];
}

function buildPoints(series: { day: string; peak: number | null }[], rows: ForecastRow[]): Point[] {
  const byDay = new Map<string, Point>();
  for (const s of series.slice(-120)) byDay.set(s.day, { day: s.day, actual: s.peak });
  for (const r of rows) {
    const point = byDay.get(r.day) ?? { day: r.day };
    point.mid = r.mid;
    point.band80 = [r.lo80, r.hi80];
    point.band95 = [r.lo95, r.hi95];
    byDay.set(r.day, point);
  }
  return [...byDay.values()].sort((a, b) => a.day.localeCompare(b.day));
}

export function Forecast({ data, title }: { data: AppData; title: string }) {
  const [mode, setMode] = useState<Mode>("holdout");
  const f = data.forecast.titles[title];

  const rows = f ? (mode === "holdout" ? f.holdout.forecast : f.projection.forecast) : [];
  const points = useMemo(() => (f ? buildPoints(f.series, rows) : []), [f, rows]);
  if (!f) return null;

  const { test } = f.backtest;
  const startDay = rows[0]?.day;
  const modelLabel = mode === "holdout" ? f.holdout.model_label : f.projection.model_label;
  const horizonRows = f.backtest.by_horizon.map((h) => ({ h: h.h, model: h.model * 100, naive: h.naive * 100 }));
  const verdict =
    test.skill_vs_naive >= 0.03
      ? `beats the simple baseline by ${pct(test.skill_vs_naive)}`
      : test.skill_vs_naive > -0.03
        ? "is no better than the simple baseline"
        : "does not beat the simple baseline";

  return (
    <section className="block" id="forecast">
      <div className="wrap">
        <header>
          <p className="eyebrow">02 · Can we project it? · {f.name}</p>
          <h2>A forecast I can defend, not just draw.</h2>
          <p className="lead">
            Four simple models compete in a rolling backtest. Each week the best one is chosen, and its confidence
            band is calibrated, using only what was known at that time. Then I check whether the "80%" band really
            contained about 80% of what happened.
          </p>
        </header>

        <div className="split">
          <div className="card">
            <div className="chart-head">
              <h3 style={{ margin: 0 }}>Daily peak concurrent players</h3>
              <div className="segmented" role="group" aria-label="Forecast view">
                <button type="button" aria-pressed={mode === "holdout"} onClick={() => setMode("holdout")}>
                  Forecast vs actual
                </button>
                <button type="button" aria-pressed={mode === "projection"} onClick={() => setMode("projection")}>
                  Project forward
                </button>
              </div>
            </div>
            <div style={{ height: 340 }}>
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={points} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
                  <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="day"
                    tickFormatter={shortDate}
                    tick={{ fill: "var(--muted)", fontSize: 11 }}
                    minTickGap={36}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    tickFormatter={compact}
                    tick={{ fill: "var(--muted)", fontSize: 11 }}
                    width={50}
                    axisLine={false}
                    tickLine={false}
                    domain={["auto", "auto"]}
                  />
                  <Tooltip
                    content={({ active, payload }) => {
                      const p = payload?.[0]?.payload as Point | undefined;
                      if (!active || !p) return null;
                      return (
                        <div className="tip">
                          {longDate(p.day)}
                          {p.actual != null && (
                            <>
                              <br />
                              actual <b>{Math.round(p.actual).toLocaleString()}</b>
                            </>
                          )}
                          {p.mid !== undefined && p.band80 && (
                            <>
                              <br />
                              forecast <b>{Math.round(p.mid).toLocaleString()}</b>
                              <br />
                              80%: {compact(p.band80[0])} to {compact(p.band80[1])}
                            </>
                          )}
                        </div>
                      );
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: 11, fontFamily: "var(--font-mono)" }} />
                  <Area
                    dataKey="band95"
                    name="95% band"
                    stroke="none"
                    fill="var(--blue)"
                    fillOpacity={0.14}
                    isAnimationActive={false}
                    connectNulls
                  />
                  <Area
                    dataKey="band80"
                    name="80% band"
                    stroke="none"
                    fill="var(--lime)"
                    fillOpacity={0.26}
                    isAnimationActive={false}
                    connectNulls
                  />
                  <Line
                    dataKey="actual"
                    name="Actual"
                    stroke="var(--fg)"
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={false}
                  />
                  <Line
                    dataKey="mid"
                    name="Forecast"
                    stroke="var(--lime)"
                    strokeWidth={2.5}
                    strokeDasharray="5 4"
                    dot={false}
                    isAnimationActive={false}
                  />
                  {startDay && (
                    <ReferenceLine
                      x={startDay}
                      stroke="var(--coral)"
                      strokeDasharray="3 3"
                      label={{ value: "forecast starts", fill: "var(--coral)", fontSize: 11, position: "insideTopRight" }}
                    />
                  )}
                </ComposedChart>
              </ResponsiveContainer>
            </div>
            <p className="chart-note">
              {mode === "holdout"
                ? `Trained only on data through ${longDate(f.holdout.cutoff)}, then compared to what really happened. Model that week: ${modelLabel}.`
                : `Projection beyond the last day of data (${longDate(f.series[f.series.length - 1]?.day ?? "")}). There is no actual to compare yet, which is why the honest evidence is the backtest.`}
            </p>
          </div>

          <div className="grid">
            <div className="card">
              <h3>Out-of-sample scorecard</h3>
              <p>
                Across {f.backtest.test_origins} weekly forecasts made after {longDate(f.backtest.calibration_end)} (
                {test.days_scored} days scored), the method {verdict}.
              </p>
              <div className="grid g2" style={{ marginTop: ".9rem" }}>
                <div className="kpi">
                  <p className="label">Error</p>
                  <p className="value">{pct(test.mape, 1)}</p>
                  <p className="note">baseline {pct(test.naive_mape, 1)}</p>
                </div>
                <div className={`kpi ${Math.abs(test.coverage80 - 0.8) <= 0.07 ? "good" : "warn"}`}>
                  <p className="label">80% band held</p>
                  <p className="value">{pct(test.coverage80)}</p>
                  <p className="note">95% band: {pct(test.coverage95)}</p>
                </div>
              </div>
            </div>

            <div className="card">
              <h3>The same method on uncleaned data</h3>
              <p>
                Skip the frozen-feed removal and the error becomes <strong>{pct(f.without_cleaning.mape, 1)}</strong>{" "}
                instead of <strong>{pct(test.mape, 1)}</strong>, and the 80% band holds{" "}
                <strong>{pct(f.without_cleaning.coverage80)}</strong> instead of <strong>{pct(test.coverage80)}</strong>
                .
              </p>
            </div>
          </div>
        </div>

        <div className="split" style={{ marginTop: "1rem" }}>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Model</th>
                  <th className="num">Error, all weeks</th>
                  <th className="num">Error, later weeks</th>
                </tr>
              </thead>
              <tbody>
                {f.backtest.models.map((m) => (
                  <tr key={m.key} className={m.chosen ? "chosen" : ""}>
                    <td>
                      {m.label} {m.chosen && <span className="chip pass">picked most often</span>}
                    </td>
                    <td className="num">{pct(m.mape_all, 1)}</td>
                    <td className="num">{pct(m.mape_test, 1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="card">
            <h3>Error by days ahead (later weeks)</h3>
            <div style={{ height: 190 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={horizonRows} margin={{ top: 6, right: 8, bottom: 0, left: 0 }}>
                  <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="h" tick={{ fill: "var(--muted)", fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis
                    tickFormatter={(v: number) => `${v.toFixed(0)}%`}
                    tick={{ fill: "var(--muted)", fontSize: 11 }}
                    width={40}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip
                    formatter={(v: number) => `${v.toFixed(1)}%`}
                    labelFormatter={(h) => `${h} days ahead`}
                    contentStyle={{ background: "var(--card)", border: "1px solid var(--border)", fontSize: 12 }}
                  />
                  <Line dataKey="model" name="Method" stroke="var(--lime)" strokeWidth={2.5} dot={false} />
                  <Line dataKey="naive" name="Same weekday last week" stroke="var(--muted)" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        <SqlViewer label="View the SQL behind the daily series" names={["04_daily_series"]} sql={data.sql} />
      </div>
    </section>
  );
}
