import { useMemo } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { compact, pct, shortDate } from "../format";
import type { AppData } from "../types";

export function Cohorts({ data }: { data: AppData }) {
  const { cohorts } = data;
  const merged = useMemo(() => {
    const byT = new Map<number, { t: number; all?: number; breakout?: number; other?: number }>();
    (["all", "breakout", "other"] as const).forEach((key) => {
      for (const p of cohorts.curves[key]) {
        const row = byT.get(p.t) ?? { t: p.t };
        row[key] = p.s * 100;
        byT.set(p.t, row);
      }
    });
    return [...byT.values()].sort((a, b) => a.t - b.t);
  }, [cohorts]);

  const b = cohorts.stats.breakout;
  const o = cohorts.stats.other;

  return (
    <section className="block" id="cohorts">
      <div className="wrap">
        <header>
          <p className="eyebrow">04 · Which launches stick?</p>
          <h2>Launch cohorts: how long new titles hold a top-100 spot.</h2>
          <p className="lead">
            Steam publishes no per-user data, so real user cohorts are impossible here. The honest analog is title
            cohorts: group titles by how strongly they launched, then compare how long they stay ranked. Titles still
            ranked when the data ends are handled with a Kaplan-Meier curve, because a plain average would be biased
            low.
          </p>
        </header>

        <div className="grid g4">
          <div className="kpi good">
            <p className="label">Breakout launches</p>
            <p className="value">{b.titles}</p>
            <p className="note">{cohorts.definition.breakout}</p>
          </div>
          <div className="kpi good">
            <p className="label">Median days ranked</p>
            <p className="value">{b.median_days ?? "n/a"}</p>
            <p className="note">vs {o.median_days ?? "n/a"} for all other launches</p>
          </div>
          <div className="kpi good">
            <p className="label">Still ranked at day 7</p>
            <p className="value">{b.survival_day7 === null ? "n/a" : pct(b.survival_day7)}</p>
            <p className="note">others: {o.survival_day7 === null ? "n/a" : pct(o.survival_day7)}</p>
          </div>
          <div className="kpi good">
            <p className="label">Still ranked at day 30</p>
            <p className="value">{b.survival_day30 === null ? "n/a" : pct(b.survival_day30)}</p>
            <p className="note">others: {o.survival_day30 === null ? "n/a" : pct(o.survival_day30)}</p>
          </div>
        </div>

        <div className="card" style={{ marginTop: "1rem" }}>
          <h3>Share of new titles still in the top 100, by days since entry</h3>
          <div style={{ height: 320 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={merged} margin={{ top: 8, right: 12, bottom: 16, left: 0 }}>
                <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="t"
                  type="number"
                  domain={[0, "dataMax"]}
                  tick={{ fill: "var(--muted)", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  label={{ value: "days since first appearing in the top 100", position: "insideBottom", offset: -8, fill: "var(--muted)", fontSize: 11 }}
                />
                <YAxis
                  tickFormatter={(v: number) => `${v.toFixed(0)}%`}
                  domain={[0, 100]}
                  tick={{ fill: "var(--muted)", fontSize: 11 }}
                  width={44}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  formatter={(v: number) => `${v.toFixed(0)}%`}
                  labelFormatter={(t) => `Day ${t}`}
                  contentStyle={{ background: "var(--card)", border: "1px solid var(--border)", fontSize: 12 }}
                />
                <Legend wrapperStyle={{ fontSize: 11, fontFamily: "var(--font-mono)" }} />
                <Line type="stepAfter" dataKey="breakout" name={`Breakout launches (n=${b.titles})`} stroke="var(--lime)" strokeWidth={3} dot={false} isAnimationActive={false} />
                <Line type="stepAfter" dataKey="other" name={`All other launches (n=${o.titles})`} stroke="var(--coral)" strokeWidth={2.5} dot={false} isAnimationActive={false} />
                <Line type="stepAfter" dataKey="all" name={`Everyone (n=${cohorts.stats.all.titles})`} stroke="var(--muted)" strokeWidth={1.5} strokeDasharray="4 4" dot={false} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <p className="chart-note">
            "Breakout" is defined from the first three days only, so it is knowable at launch. Using a title's lifetime
            peak would build in hindsight.
          </p>
        </div>

        <h3 className="eyebrow" style={{ margin: "1.8rem 0 .7rem" }}>Battle-royale launches in the window</h3>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Title</th>
                <th>Entered</th>
                <th className="num">Days ranked</th>
                <th className="num">Peak players</th>
                <th className="num">Day 7 vs launch</th>
                <th className="num">Day 30 vs launch</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {cohorts.scorecard.map((r) => (
                <tr key={r.title}>
                  <td><strong>{r.title}</strong></td>
                  <td className="mono">{shortDate(r.entered)}</td>
                  <td className="num">{r.days_ranked}</td>
                  <td className="num">{compact(r.peak_ccu)}</td>
                  <td className="num">{r.day7_index === null ? "n/a" : pct(r.day7_index)}</td>
                  <td className="num">{r.day30_index === null ? "n/a" : pct(r.day30_index)}</td>
                  <td><span className={`chip ${r.status === "still ranked" ? "pass" : "warn"}`}>{r.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="chart-note">
          Only {cohorts.scorecard.length} titles, labeled by hand from their names, so read this as a scorecard, not a
          statistic. "Day 7 vs launch" compares that day's peak to the title's best day in its first three. Entrant =
          {" "}{cohorts.definition.entrant}. Exit = {cohorts.definition.exit}.
        </p>
      </div>
    </section>
  );
}
