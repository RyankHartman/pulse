"""Anomaly detection that asks "is it real?" before "what happened?".

For each focus title we strip the weekly cycle and the slow trend (robust STL), then flag days
whose residual is extreme. Every flagged event is then classified:

* data_suspect  : the event sits on or next to a day we had to interpolate (coverage problem)
* platform_wide : many other long-running titles moved the same way that day
* title_specific: neither of the above, so the title itself changed
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import STL

from common import impute_log, title_series
from config import ANOMALY_MIN_PCT, ANOMALY_Z, FOCUS_TITLES, PLATFORM_SHARE, PLATFORM_Z, SHORT_NAMES

CLASS_LABELS = {
    "title_specific": "Title-specific",
    "platform_wide": "Platform-wide",
    "data_suspect": "Data suspect",
}


def _trim(series: pd.DataFrame) -> pd.DataFrame:
    usable = series["usable"]
    return series.loc[usable.idxmax() : usable[::-1].idxmax()]


def residual_z(series: pd.DataFrame):
    """Robust z-score of the STL residual of log daily peak. NaN on unusable days."""
    y = impute_log(series["peak"])
    fit = STL(y.to_numpy(), period=7, robust=True).fit()
    resid = pd.Series(fit.resid, index=y.index)
    observed = series["usable"]
    base = resid[observed]
    median = base.median()
    scale = 1.4826 * (base - median).abs().median()
    z = (resid - median) / scale
    z[~observed] = np.nan
    expected = pd.Series(np.exp(y.to_numpy() - fit.resid), index=y.index)
    return z, expected


def platform_signal(daily: pd.DataFrame, min_days: int = 290):
    """Share of long-running titles that jumped / dropped on each day."""
    z_by_title = {}
    for title, group in daily.groupby("title"):
        series = title_series(daily, title)
        series = _trim(series) if series["usable"].any() else series
        if series["usable"].sum() < min_days:
            continue
        z, _ = residual_z(series)
        z_by_title[title] = z
    z_frame = pd.DataFrame(z_by_title)
    seen = z_frame.notna().sum(axis=1).replace(0, np.nan)
    up = (z_frame >= PLATFORM_Z).sum(axis=1) / seen
    down = (z_frame <= -PLATFORM_Z).sum(axis=1) / seen
    return up, down, len(z_by_title)


def find_events(series, z, expected, up, down):
    deviation = (series["peak"] / expected - 1).abs()
    flagged = (z.abs() >= ANOMALY_Z) & (deviation >= ANOMALY_MIN_PCT / 100)
    days = list(z.index[flagged.fillna(False)])
    groups, current = [], []
    for day in days:
        if current and ((day - current[-1]).days > 1 or np.sign(z[day]) != np.sign(z[current[-1]])):
            groups.append(current)
            current = []
        current.append(day)
    if current:
        groups.append(current)

    events = []
    for g in groups:
        peak_day = max(g, key=lambda d: abs(z[d]))
        direction = "spike" if z[peak_day] > 0 else "drop"
        window = pd.date_range(g[0] - pd.Timedelta(days=1), g[-1] + pd.Timedelta(days=1))
        window = [d for d in window if d in series.index]
        suspect = bool((~series.loc[window, "usable"]).any())
        share_series = up if direction == "spike" else down
        share = float(share_series.reindex(g).max())
        if suspect:
            cls, why = "data_suspect", "Next to a day with missing hourly snapshots, so the daily peak may be distorted."
        elif share >= PLATFORM_SHARE:
            cls = "platform_wide"
            why = f"{share:.0%} of long-running titles moved the same way, so this is not specific to the title."
        else:
            cls = "title_specific"
            why = f"Only {share:.0%} of long-running titles moved the same way, so the title itself changed."
        events.append(
            {
                "start": g[0],
                "end": g[-1],
                "peak_day": peak_day,
                "direction": direction,
                "days": len(g),
                "z": float(z[peak_day]),
                "actual": float(series.loc[peak_day, "peak"]),
                "expected": float(expected[peak_day]),
                "pct_vs_expected": float(100 * (series.loc[peak_day, "peak"] / expected[peak_day] - 1)),
                "platform_share": share,
                "class": cls,
                "class_label": CLASS_LABELS[cls],
                "why": why,
            }
        )
    return events


def build(daily: pd.DataFrame) -> dict:
    up, down, n_platform = platform_signal(daily)
    titles = {}
    for title in FOCUS_TITLES:
        series = _trim(title_series(daily, title))
        z, expected = residual_z(series)
        events = find_events(series, z, expected, up, down)
        titles[title] = {
            "title": title,
            "name": SHORT_NAMES.get(title, title),
            "series": [
                {
                    "day": d,
                    "peak": None if np.isnan(p) else float(p),
                    "expected": float(expected[d]),
                    "z": None if np.isnan(z[d]) else float(z[d]),
                }
                for d, p in series["peak"].items()
            ],
            "events": events,
            "counts": {
                key: sum(1 for e in events if e["class"] == key) for key in CLASS_LABELS
            },
        }
    platform_days = [
        {"day": d, "up": None if np.isnan(u) else float(u), "down": None if np.isnan(dn) else float(dn)}
        for d, u, dn in zip(up.index, up.values, down.values)
    ]
    return {
        "thresholds": {
            "z": ANOMALY_Z,
            "min_pct": ANOMALY_MIN_PCT,
            "platform_z": PLATFORM_Z,
            "platform_share": PLATFORM_SHARE,
        },
        "platform_titles": n_platform,
        "platform": platform_days,
        "titles": titles,
    }
