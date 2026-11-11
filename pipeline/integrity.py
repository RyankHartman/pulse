"""Data-integrity report: what is wrong with the raw data and what we did about it."""
from __future__ import annotations

import pandas as pd

from config import DATASET, MIN_HOURS_FOR_DAY, WINDOW_END, WINDOW_START
from load import read_sql


def build(con) -> dict:
    q = lambda sql: con.execute(sql).fetchdf()

    raw = q("""
        select count(*) as n_rows, count(distinct title) as n_titles,
               min(day) as first_day, max(day) as last_day,
               count(distinct ts) as snapshots
        from obs
    """).iloc[0]
    deduped_rows = int(q("select count(*) as n from deduped").iloc[0]["n"])
    clean_rows = int(q("select count(*) as n from clean").iloc[0]["n"])
    per_snapshot = q("select count(*) as n from obs group by ts")["n"]
    raw_snapshots = int(raw["snapshots"])

    # --- frozen feed --------------------------------------------------------
    stale = q("select ts, share_unchanged from stale_snapshots order by ts")
    stale["ts"] = pd.to_datetime(stale["ts"])
    stale_ts = set(stale["ts"])
    stale_runs = q(read_sql("03_stale_runs"))
    stale_runs["run_start"] = pd.to_datetime(stale_runs["run_start"])
    stale_runs["run_end"] = pd.to_datetime(stale_runs["run_end"])
    long_freezes = stale_runs[stale_runs["frozen_hours"] >= 6]
    normal = q("select share_unchanged from snapshot_change")["share_unchanged"]
    typical_unchanged = float((normal[normal < 0.5]).quantile(0.99))

    # --- coverage (after removing frozen snapshots) ---------------------------
    coverage = q(read_sql("05_coverage"))
    expected = len(coverage)
    usable = int(coverage["present"].sum())
    coverage["ts"] = pd.to_datetime(coverage["ts"])
    coverage["day"] = coverage["ts"].dt.normalize()
    per_day = coverage.groupby("day")["present"].sum().astype(int)
    frozen_per_day = stale.assign(day=stale["ts"].dt.normalize()).groupby("day").size()
    calendar = [
        {"day": d, "hours": int(h), "frozen": int(frozen_per_day.get(d, 0))} for d, h in per_day.items()
    ]

    outages = q(read_sql("06_outages"))
    outages["outage_start"] = pd.to_datetime(outages["outage_start"])
    outages["outage_end"] = pd.to_datetime(outages["outage_end"])
    first_ts = pd.Timestamp(WINDOW_START)
    last_ts = pd.Timestamp(WINDOW_END) + pd.Timedelta(hours=23)

    def kind(row) -> str:
        # Missing hours touching the very start / end are the collector starting and
        # stopping mid-day, not an outage in the middle of the series.
        if row["outage_start"] == first_ts:
            return "collection started mid-day"
        if row["outage_end"] == last_ts:
            return "collection ended mid-day"
        hours_in_run = int(row["missing_hours"])
        frozen_in_run = sum(1 for t in stale_ts if row["outage_start"] <= t <= row["outage_end"])
        return "frozen feed" if frozen_in_run >= 0.5 * hours_in_run else "outage"

    outages["kind"] = outages.apply(kind, axis=1)
    outage_rows = [
        {"start": r.outage_start, "end": r.outage_end, "hours": int(r.missing_hours), "kind": r.kind}
        for r in outages.itertuples()
        if r.missing_hours >= 6
    ]
    true_outages = outages[outages["kind"] == "outage"]
    longest = true_outages.iloc[0] if len(true_outages) else None

    missing_days = [d for d, h in per_day.items() if h == 0]
    partial_days = [d for d, h in per_day.items() if 0 < h < MIN_HOURS_FOR_DAY]
    nearly_full_days = [d for d, h in per_day.items() if MIN_HOURS_FOR_DAY <= h < 24]

    # --- duplicates & rank order -------------------------------------------
    dup = q(read_sql("07_duplicates"))
    dup["ts"] = pd.to_datetime(dup["ts"])
    rank_violations = int(q(read_sql("08_rank_order")).iloc[0]["violations"])

    # --- do the minor defects cluster? ---------------------------------------
    window = q(read_sql("10_defect_window"))
    window["first_ts"] = pd.to_datetime(window["first_ts"])
    window["last_ts"] = pd.to_datetime(window["last_ts"])
    counts = {r.defect: int(r.n) for r in window.itertuples()}
    window_start, window_end = window["first_ts"].min(), window["last_ts"].max()
    window_days = (window_end - window_start).days + 1
    clustered = window_days <= 7 and sum(counts.values()) > 0

    # --- value sanity -------------------------------------------------------
    odd = q("""
        select
            sum((current_players is null)::int)  as nulls,
            sum((current_players <= 0)::int)     as non_positive,
            sum((peak_players < current_players)::int) as peak_below_current
        from obs
    """).iloc[0]

    # One concrete picture of the frozen feed: PUBG hour by hour around the worst freeze.
    example_rows = q("""
        select d.ts, d.current_players as ccu, (s.ts is not null) as frozen
        from deduped d
        left join stale_snapshots s using (ts)
        where d.title = 'PLAYERUNKNOWN''S BATTLEGROUNDS'
          and d.day between date '2019-01-22' and date '2019-01-24'
        order by d.ts
    """)
    example = [
        {"ts": pd.Timestamp(r.ts), "ccu": int(r.ccu), "frozen": bool(r.frozen)} for r in example_rows.itertuples()
    ]

    freeze_text = ", ".join(
        f"{r.run_start:%b %d} ({int(r.frozen_hours)}h)" for r in long_freezes.itertuples()
    )
    checks = [
        {
            "check": "Every snapshot lists 100 titles",
            "result": f"{int((per_snapshot == 100).sum()):,} of {len(per_snapshot):,} snapshots",
            "status": "pass" if (per_snapshot == 100).all() else "warn",
            "action": "None needed. But note: this check passes on the frozen snapshots below, which is why it is not enough.",
        },
        {
            "check": "Frozen feed (values identical to the previous hour)",
            "result": f"{len(stale)} snapshots in {len(stale_runs)} runs. Long freezes: {freeze_text}",
            "status": "fail",
            "action": f"Caught by comparing values, not row counts. 99% of healthy snapshots have under "
            f"{max(typical_unchanged, 0.01):.0%} of titles unchanged, while these have 50 to 100%. Dropped and treated "
            "as missing, which makes the two long-freeze days unusable for daily peaks.",
        },
        {
            "check": "Hourly snapshots present and trustworthy",
            "result": f"{usable:,} of {expected:,} ({100 * usable / expected:.1f}%). "
            f"{expected - raw_snapshots} never collected, {len(stale)} frozen",
            "status": "warn",
            "action": f"A day only counts as observed if it keeps {MIN_HOURS_FOR_DAY}+ of 24 snapshots. "
            "Other days are treated as missing, never as zero.",
        },
        {
            "check": "Outages in the middle of the series",
            "result": (
                f"longest {int(longest['missing_hours'])}h "
                f"({longest['outage_start']:%b %d} to {longest['outage_end']:%b %d})"
                if longest is not None
                else "none"
            ),
            "status": "warn",
            "action": "Interpolated in log space for model fitting only. Never scored as real observations.",
        },
        {
            "check": "Partial first and last day",
            "result": f"{WINDOW_START:%b %d} starts at 13:00 and {WINDOW_END:%b %d} ends at 13:00",
            "status": "warn",
            "action": "Dropped from daily series. A truncated day would understate its true peak.",
        },
        {
            "check": "Duplicate (title, hour) rows",
            "result": f"{len(dup)} pairs, all with conflicting player counts "
            f"(median gap {dup['gap_pct'].median():.1f}%, max {dup['gap_pct'].max():.1f}%)",
            "status": "warn" if len(dup) else "pass",
            "action": "Kept the best-ranked row per title and hour. Likely the leaderboard moving between paged requests.",
        },
        {
            "check": "Do the minor defects cluster?",
            "result": (
                f"Yes. All {counts.get('duplicate rows', 0)} duplicate rows, "
                f"{counts.get('partially frozen snapshots', 0)} partly frozen snapshots and "
                f"{counts.get('rank-order violations', 0)} rank-order violations fall between "
                f"{window_start:%b %d} and {window_end:%b %d}, 2018"
                if clustered
                else "No. They are spread across the file"
            ),
            "status": "warn",
            "action": "One collector incident, not three problems. Duplicates are collapsed. The partly frozen snapshots "
            "are kept (under 0.3% of hours, most titles in them are fresh) and noted as a limitation.",
        },
        {
            "check": "Rank order matches player counts",
            "result": f"{rank_violations} violations across {len(per_snapshot):,} snapshots",
            "status": "warn" if rank_violations else "pass",
            "action": "Ranks are not used in any model. Only player counts are.",
        },
        {
            "check": "Nulls, zeros, and impossible values",
            "result": f"{int(odd['nulls'])} nulls, {int(odd['non_positive'])} non-positive, "
            f"{int(odd['peak_below_current'])} where peak < current",
            "status": "pass",
            "action": "None needed.",
        },
        {
            "check": "Time zone of the hour field",
            "result": "Not documented by the dataset",
            "status": "warn",
            "action": "Treated as a consistent label. Weekly patterns are unaffected and hour-of-day claims are avoided.",
        },
    ]

    return {
        "dataset": DATASET,
        "summary": {
            "rows": int(raw["n_rows"]),
            "rows_after_dedupe": deduped_rows,
            "rows_clean": clean_rows,
            "titles": int(raw["n_titles"]),
            "first_day": raw["first_day"],
            "last_day": raw["last_day"],
            "snapshots": raw_snapshots,
            "expected_snapshots": expected,
            "never_collected": expected - raw_snapshots,
            "frozen_snapshots": len(stale),
            "frozen_runs": len(stale_runs),
            "usable_snapshots": usable,
            "raw_coverage_pct": round(100 * raw_snapshots / expected, 2),
            "usable_coverage_pct": round(100 * usable / expected, 2),
            "missing_days": missing_days,
            "partial_days": partial_days,
            "nearly_full_days": len(nearly_full_days),
            "defect_window": {
                "clustered": clustered,
                "start": window_start,
                "end": window_end,
                "days": window_days,
                "duplicates": counts.get("duplicate rows", 0),
                "partial_freezes": counts.get("partially frozen snapshots", 0),
                "rank_violations": counts.get("rank-order violations", 0),
            },
            "duplicate_pairs": len(dup),
            "rank_violations": rank_violations,
            "longest_outage_hours": int(longest["missing_hours"]) if longest is not None else 0,
            "long_freezes": [
                {"start": r.run_start, "end": r.run_end, "hours": int(r.frozen_hours)}
                for r in long_freezes.itertuples()
            ],
        },
        "outages": outage_rows,
        "frozen_example": {"title": "PUBG", "points": example},
        "calendar": calendar,
        "checks": checks,
    }
