"""Launch-cohort analysis: how long do new titles hold a top-100 spot?

Steam exposes no per-user data, so true user cohorts are impossible here. The honest analog is
title cohorts: group titles by when and how they entered, and compare how long they stay ranked.

Titles still ranked on the last day are *censored* (we don't know when they will leave), so the
survival curve uses Kaplan-Meier instead of a naive average, which would be biased low.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import (
    BR_ENTRANTS,
    BREAKOUT_EARLY_PEAK,
    ENTRANT_AFTER,
    EXIT_GAP_DAYS,
    WINDOW_END,
)
from load import read_sql

MAX_T = 120


def kaplan_meier(durations: np.ndarray, exited: np.ndarray) -> list[dict]:
    survival, points = 1.0, [{"t": 0, "s": 1.0, "at_risk": int(len(durations))}]
    for t in range(1, MAX_T + 1):
        at_risk = int((durations >= t).sum())
        if at_risk == 0:
            break
        events = int(((durations == t) & exited).sum())
        survival *= 1 - events / at_risk
        points.append({"t": t, "s": float(survival), "at_risk": at_risk})
    return points


def median_survival(points: list[dict]):
    for p in points:
        if p["s"] <= 0.5:
            return p["t"]
    return None


def build(con, daily: pd.DataFrame) -> dict:
    ent = con.execute(read_sql("09_entrants")).fetchdf()
    ent["first_day"] = pd.to_datetime(ent["first_day"])
    ent["last_day"] = pd.to_datetime(ent["last_day"])
    end = pd.Timestamp(WINDOW_END)

    entrants = ent[ent["first_day"] > pd.Timestamp(ENTRANT_AFTER)].copy()
    entrants["lifetime"] = (entrants["last_day"] - entrants["first_day"]).dt.days + 1
    entrants["exited"] = (end - entrants["last_day"]).dt.days >= EXIT_GAP_DAYS
    # "Breakout" uses only the first three days, which is knowable at launch. Using a title's
    # lifetime peak would be look-ahead bias: long-lived titles trivially have higher peaks.
    merged = daily.merge(entrants[["title", "first_day"]], on="title")
    in_window = (merged["day"] >= merged["first_day"]) & (merged["day"] <= merged["first_day"] + pd.Timedelta(days=2))
    entrants["early_peak"] = entrants["title"].map(merged[in_window].groupby("title")["daily_peak"].max())
    entrants["breakout"] = entrants["early_peak"] >= BREAKOUT_EARLY_PEAK

    groups = {
        "all": entrants,
        "breakout": entrants[entrants["breakout"]],
        "other": entrants[~entrants["breakout"]],
    }
    curves, stats = {}, {}
    for key, frame in groups.items():
        points = kaplan_meier(frame["lifetime"].to_numpy(), frame["exited"].to_numpy())
        curves[key] = points
        stats[key] = {
            "titles": int(len(frame)),
            "exited": int(frame["exited"].sum()),
            "still_ranked": int((~frame["exited"]).sum()),
            "median_days": median_survival(points),
            "survival_day7": next((p["s"] for p in points if p["t"] == 7), None),
            "survival_day30": next((p["s"] for p in points if p["t"] == 30), None),
        }

    # Battle-royale launch scorecard (titles labelled by hand from their names).
    by_title = daily.set_index(["title", "day"])["daily_peak"]
    scorecard = []
    for title in BR_ENTRANTS:
        row = ent[ent["title"] == title]
        if row.empty:
            continue
        row = row.iloc[0]
        peaks = by_title.xs(title, level="title")
        first = row["first_day"]
        early = peaks[(peaks.index >= first) & (peaks.index <= first + pd.Timedelta(days=2))].max()
        day7 = peaks.get(first + pd.Timedelta(days=7))
        day30 = peaks.get(first + pd.Timedelta(days=30))
        exited = (end - row["last_day"]).days >= EXIT_GAP_DAYS
        scorecard.append(
            {
                "title": title,
                "entered": first,
                "last_seen": row["last_day"],
                "days_ranked": int(row["active_days"]),
                "peak_ccu": int(row["peak_ccu"]),
                "day7_index": None if day7 is None or pd.isna(day7) else float(day7 / early),
                "day30_index": None if day30 is None or pd.isna(day30) else float(day30 / early),
                "status": "exited" if exited else "still ranked",
            }
        )
    scorecard.sort(key=lambda r: -r["days_ranked"])

    return {
        "definition": {
            "entrant": f"first appears in the top 100 after {ENTRANT_AFTER:%b %d, %Y}",
            "exit": f"absent for {EXIT_GAP_DAYS}+ days before the data ends",
            "breakout": f"{BREAKOUT_EARLY_PEAK:,}+ peak concurrent players within its first three days",
        },
        "curves": curves,
        "stats": stats,
        "scorecard": scorecard,
    }
