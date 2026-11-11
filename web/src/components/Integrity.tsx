import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { compact, hourLabel, longDate, shortDate } from "../format";
import type { AppData, CalendarDay } from "../types";
import { SqlViewer } from "./SqlViewer";

function dayClass(day: CalendarDay): string {
  const base = day.hours === 0 ? "none" : day.hours >= 24 ? "" : day.hours >= 20 ? "partial" : "bad";
  return `cal-day ${base} ${day.frozen >= 6 ? "frozen" : ""}`.trim();
}

function dayTitle(day: CalendarDay): string {
  const frozen = day.frozen ? `, ${day.frozen} frozen` : "";
  return `${longDate(day.day)}: ${day.hours} of 24 snapshots usable${frozen}`;
}

export function Integrity({ data }: { data: AppData }) {
  const { integrity, sql } = data;
  const s = integrity.summary;
  const points = integrity.frozen_example.points.map((p) => ({
    ts: p.ts,
    live: p.frozen ? null : p.ccu,
    frozen: p.frozen ? p.ccu : null,
  }));
  const freeze = s.long_freezes[0];

  return (
    <section className="block" id="integrity">
      <div className="wrap">
        <header>
          <p className="eyebrow">01 · Can we trust the data?</p>
          <h2>Row counts said the data was fine. The values said otherwise.</h2>
          <p className="lead">
            Before modeling anything, I audited the raw file. The most important finding is one a row-count check
            cannot see.
          </p>
        </header>

        <div className="grid g4">
          <div className="kpi good">
            <p className="label">Usable hourly snapshots</p>
            <p className="value">{s.usable_coverage_pct}%</p>
            <p className="note">
              {s.usable_snapshots.toLocaleString()} of {s.expected_snapshots.toLocaleString()}
            </p>
          </div>
          <div className="kpi warn">
            <p className="label">Frozen snapshots</p>
            <p className="value">{s.frozen_snapshots}</p>
            <p className="note">in {s.frozen_runs} runs, dropped</p>
          </div>
          <div className="kpi">
            <p className="label">Never collected</p>
            <p className="value">{s.never_collected}</p>
            <p className="note">longest gap {s.longest_outage_hours}h</p>
          </div>
          <div className="kpi">
            <p className="label">Conflicting duplicates</p>
            <p className="value">{s.duplicate_pairs}</p>
            <p className="note">out of {s.rows.toLocaleString()} rows</p>
          </div>
        </div>

        <div className="callout" style={{ marginTop: "1.2rem" }}>
          <p>
            <strong>The finding: a frozen feed.</strong>{" "}
            {freeze
              ? `On ${longDate(freeze.start)}, for ${freeze.hours} hours straight, every title reported the exact same number as the hour before. `
              : ""}
            All 100 rows were present, so the completeness check passed. The values were stale. Left in, it looked
            like PUBG lost 63% of its players for a day and recovered, and it badly distorted the forecast evaluation.
          </p>
        </div>

        {s.defect_window.clustered && (
          <div className="callout" style={{ marginTop: "1rem" }}>
            <p>
              <strong>A second, smaller finding: one bad week.</strong> The{" "}
              {s.defect_window.duplicates} conflicting duplicate rows, {s.defect_window.partial_freezes} partly frozen
              snapshots and {s.defect_window.rank_violations} rank-order violations look like three problems. They all
              fall between {longDate(s.defect_window.start)} and {longDate(s.defect_window.end)}, which points to a
              single collector incident. I collapsed the duplicates and kept the rest, since together they are under
              0.3% of the data. It is a limitation to know about, not a reason to distrust the whole file.
            </p>
          </div>
        )}

        <div className="card" style={{ marginTop: "1rem" }}>
          <h3>PUBG, hour by hour, Jan 22 to 24. Coral = frozen values</h3>
          <div style={{ height: 260 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={points} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
                <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="ts"
                  tickFormatter={shortDate}
                  tick={{ fill: "var(--muted)", fontSize: 11 }}
                  minTickGap={40}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tickFormatter={compact}
                  tick={{ fill: "var(--muted)", fontSize: 11 }}
                  width={48}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  content={({ active, payload }) => {
                    const row = payload?.[0]?.payload as (typeof points)[number] | undefined;
                    if (!active || !row) return null;
                    const value = row.live ?? row.frozen ?? 0;
                    return (
                      <div className="tip">
                        {hourLabel(row.ts)}
                        <br />
                        <b>{value.toLocaleString()}</b> players
                        {row.frozen !== null ? " (frozen)" : ""}
                      </div>
                    );
                  }}
                />
                <Line dataKey="live" stroke="var(--lime)" strokeWidth={2} dot={false} isAnimationActive={false} />
                <Line dataKey="frozen" stroke="var(--coral)" strokeWidth={3} dot={false} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <p className="chart-note">
            Found by comparing each title's value to its previous hour. 99% of healthy snapshots have under 2% of
            titles unchanged. These had 100%.
          </p>
        </div>

        <div className="card" style={{ marginTop: "1rem" }}>
          <h3>Every day of the collection window, by usable snapshots</h3>
          <div className="calendar" role="img" aria-label="Calendar of daily data coverage">
            {integrity.calendar.map((day) => (
              <span key={day.day} className={dayClass(day)} title={dayTitle(day)} />
            ))}
          </div>
          <div className="legend">
            <span><i style={{ background: "var(--lime)" }} /> all 24 hours</span>
            <span><i style={{ background: "color-mix(in oklab, var(--lime) 45%, var(--bg))" }} /> 20 to 23 hours</span>
            <span><i style={{ background: "var(--coral)" }} /> under 20 hours (unusable)</span>
            <span><i style={{ background: "var(--red)" }} /> no data</span>
            <span><i style={{ background: "var(--surface)", outline: "2px solid var(--blue)" }} /> frozen feed 6h+</span>
          </div>
        </div>

        <div className="table-wrap" style={{ marginTop: "1rem" }}>
          <table>
            <thead>
              <tr>
                <th>Check</th>
                <th>Result</th>
                <th>Status</th>
                <th>What I did about it</th>
              </tr>
            </thead>
            <tbody>
              {integrity.checks.map((check) => (
                <tr key={check.check}>
                  <td><strong>{check.check}</strong></td>
                  <td>{check.result}</td>
                  <td><span className={`chip ${check.status}`}>{check.status}</span></td>
                  <td className="muted">{check.action}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <SqlViewer
          label="View the SQL behind the cleaning"
          names={["00_dedupe", "01_stale_snapshots", "02_clean", "03_stale_runs", "10_defect_window"]}
          sql={sql}
        />
      </div>
    </section>
  );
}
