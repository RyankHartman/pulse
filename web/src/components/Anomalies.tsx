import {
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { compact, longDate, shortDate } from "../format";
import type { AnomalyEvent, AppData } from "../types";

const CLASS_COLOR: Record<AnomalyEvent["class"], string> = {
  title_specific: "var(--lime)",
  platform_wide: "var(--blue)",
  data_suspect: "var(--coral)",
};

const range = (e: AnomalyEvent) =>
  e.start === e.end ? shortDate(e.start) : `${shortDate(e.start)} to ${shortDate(e.end)}`;

export function Anomalies({ data, title }: { data: AppData; title: string }) {
  const a = data.anomalies.titles[title];
  if (!a) return null;
  const t = data.anomalies.thresholds;

  return (
    <section className="block" id="anomalies">
      <div className="wrap">
        <header>
          <p className="eyebrow">03 · What changed, and is it real? · {a.name}</p>
          <h2>Flag the spike. Then ask whether it's us, the platform, or the data.</h2>
          <p className="lead">
            Weekly rhythm and slow trend are stripped out first. A day is flagged only if it is statistically extreme
            (robust z of {t.z} or more) <em>and</em> moves the number by at least {t.min_pct}%. Each flag is then
            classified, because a PM should only chase the ones the product caused.
          </p>
        </header>

        <div className="grid g3" style={{ marginBottom: "1rem" }}>
          <div className="card">
            <span className="chip title_specific">Title-specific</span>
            <p style={{ marginTop: ".6rem" }}>
              Still unusual after checking the platform. Candidates for a product explanation.
            </p>
          </div>
          <div className="card">
            <span className="chip platform_wide">Platform-wide</span>
            <p style={{ marginTop: ".6rem" }}>
              {Math.round(t.platform_share * 100)}%+ of {data.anomalies.platform_titles} long-running titles moved the
              same way that day, so the cause is not this title.
            </p>
          </div>
          <div className="card">
            <span className="chip data_suspect">Data suspect</span>
            <p style={{ marginTop: ".6rem" }}>
              Sits next to a day with missing or frozen data, so the number itself is in doubt.
            </p>
          </div>
        </div>

        <div className="card">
          <h3>Daily peak vs what the weekly pattern and trend predicted</h3>
          <div style={{ height: 320 }}>
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={a.series} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
                <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="day"
                  tickFormatter={shortDate}
                  tick={{ fill: "var(--muted)", fontSize: 11 }}
                  minTickGap={40}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tickFormatter={compact}
                  tick={{ fill: "var(--muted)", fontSize: 11 }}
                  width={50}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  content={({ active, payload }) => {
                    const p = payload?.[0]?.payload as (typeof a.series)[number] | undefined;
                    if (!active || !p) return null;
                    return (
                      <div className="tip">
                        {longDate(p.day)}
                        <br />
                        actual <b>{p.peak == null ? "no usable data" : Math.round(p.peak).toLocaleString()}</b>
                        <br />
                        expected {Math.round(p.expected).toLocaleString()}
                      </div>
                    );
                  }}
                />
                <Legend wrapperStyle={{ fontSize: 11, fontFamily: "var(--font-mono)" }} />
                <Line
                  dataKey="expected"
                  name="Expected (trend + weekly cycle)"
                  stroke="var(--muted)"
                  strokeWidth={1.5}
                  strokeDasharray="4 4"
                  dot={false}
                  isAnimationActive={false}
                />
                <Line dataKey="peak" name="Actual daily peak" stroke="var(--fg)" strokeWidth={1.8} dot={false} isAnimationActive={false} />
                {a.events.map((e) => (
                  <ReferenceDot
                    key={e.peak_day}
                    x={e.peak_day}
                    y={e.actual}
                    r={6}
                    fill={CLASS_COLOR[e.class]}
                    stroke="var(--bg)"
                    strokeWidth={2}
                    ifOverflow="extendDomain"
                  />
                ))}
              </ComposedChart>
            </ResponsiveContainer>
          </div>
          <p className="chart-note">Dots mark flagged events, colored by classification.</p>
        </div>

        <div className="table-wrap" style={{ marginTop: "1rem" }}>
          <table>
            <thead>
              <tr>
                <th>When</th>
                <th>Move</th>
                <th className="num">vs expected</th>
                <th>Class</th>
                <th>Why it was classified that way</th>
              </tr>
            </thead>
            <tbody>
              {a.events.length === 0 && (
                <tr>
                  <td colSpan={5} className="muted">No events cleared both thresholds for this title.</td>
                </tr>
              )}
              {a.events.map((e) => (
                <tr key={e.peak_day}>
                  <td className="mono">{range(e)}</td>
                  <td>{e.direction === "spike" ? "▲ spike" : "▼ drop"}</td>
                  <td className="num">{`${e.pct_vs_expected >= 0 ? "+" : ""}${e.pct_vs_expected.toFixed(0)}%`}</td>
                  <td><span className={`chip ${e.class}`}>{e.class_label}</span></td>
                  <td className="muted">{e.why}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="chart-note">
          This dataset has no patch, sale, or event calendar, so Pulse can say a title-specific event happened but not
          why. Joining a live-ops calendar is the obvious next step.
        </p>
      </div>
    </section>
  );
}
