"""Plain-English executive summary generated from the computed numbers.

Deterministic on purpose: every sentence is a template filled from a figure the pipeline
computed, so nothing is invented and the same input always gives the same note.
"""
from __future__ import annotations

import pandas as pd

from config import SHORT_NAMES


def possessive(name: str) -> str:
    return f"{name}'" if name.endswith("s") else f"{name}'s"


def when(value) -> str:
    return pd.Timestamp(value).strftime("%b %d")


def fmt(n: float) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 10_000:
        return f"{n / 1000:.0f}K"
    if n >= 1_000:
        return f"{n / 1000:.1f}K"
    return f"{n:.0f}"


def accuracy_verdict(skill: float) -> str:
    if skill >= 0.03:
        return f"That beats the baseline by {skill:.0%}."
    if skill > -0.03:
        return "No meaningful edge over the baseline, so the simpler method would do."
    return "The model did not beat the baseline here. Extra complexity did not pay for itself."


def coverage_verdict(cov80: float) -> str:
    if cov80 < 0.73:
        return (
            "The band was too narrow, which usually means the series became more volatile than the "
            "period used to calibrate it. I would recalibrate on a rolling window and monitor coverage weekly."
        )
    if cov80 > 0.87:
        return "The band is safe but looser than it needs to be."
    return "That is close to the 80% target, so the band is trustworthy."


def build(forecast: dict, anomalies: dict, integrity: dict) -> dict:
    titles = {}
    for title, f in forecast["titles"].items():
        name = SHORT_NAMES.get(title, title)
        a = anomalies["titles"][title]
        bt, test = f["backtest"], f["backtest"]["test"]
        trend, holdout = f["trend"], f["holdout"]
        last = holdout["forecast"][-1]
        counts = a["counts"]
        inside = last["actual"] is not None and last["lo80"] <= last["actual"] <= last["hi80"]
        actual_text = fmt(last["actual"]) if last["actual"] is not None else "n/a"

        headline = (
            f"{possessive(name)} daily peak {'fell' if trend['change_pct'] < 0 else 'rose'} "
            f"{abs(trend['change_pct']):.0f}% across the window. "
            f"14-day forecasts were off by {test['mape']:.0%} on average, "
            f"and the 80% band held {test['coverage80']:.0%} of the time."
        )

        bullets = [
            {
                "label": "Trend",
                "text": f"Daily peak averaged {fmt(trend['first28'])} in the first four weeks and "
                f"{fmt(trend['last28'])} in the last four ({trend['change_pct']:+.0f}%).",
            },
            {
                "label": "Forecast accuracy",
                "text": f"Out of sample, 14-day forecasts were off by {test['mape']:.1%} on average. "
                f"The 'same weekday last week' baseline was off by {test['naive_mape']:.1%}. "
                f"{accuracy_verdict(test['skill_vs_naive'])}",
            },
            {
                "label": "Can the bands be trusted?",
                "text": f"The 80% band contained the real value {test['coverage80']:.0%} of the time and "
                f"the 95% band {test['coverage95']:.0%}, over {test['days_scored']} scored days. "
                f"{coverage_verdict(test['coverage80'])}",
            },
            {
                "label": "Holdout check",
                "text": f"Forecasting from {when(holdout['cutoff'])}, day 14 ({when(last['day'])}) came out at "
                f"{fmt(last['mid'])} (80% band {fmt(last['lo80'])} to {fmt(last['hi80'])}). "
                f"The actual value was {actual_text}, "
                f"{'inside' if inside else 'outside'} the band.",
            },
            {
                "label": "Anomalies",
                "text": f"{len(a['events'])} {'event' if len(a['events']) == 1 else 'events'} flagged: {counts['title_specific']} title-specific, "
                f"{counts['platform_wide']} platform-wide, {counts['data_suspect']} sitting next to "
                f"a data gap. Only the title-specific ones are candidates for a product explanation.",
            },
            {
                "label": "Data caveat",
                "text": f"{f['imputed_days']} of {len(f['series'])} days were interpolated for model "
                f"fitting and were never scored. Usable snapshot coverage after cleaning is "
                f"{integrity['summary']['usable_coverage_pct']}%.",
            },
        ]
        raw = f.get("without_cleaning")
        if raw and abs(raw["mape"] - test["mape"]) >= 0.015:
            bullets.append(
                {
                    "label": "What the integrity check was worth",
                    "text": f"Run the identical method on the data WITHOUT removing frozen snapshots and the "
                    f"forecast error is {raw['mape']:.1%} instead of {test['mape']:.1%}, and the 80% band holds "
                    f"{raw['coverage80']:.0%} of the time instead of {test['coverage80']:.0%}. "
                    + (
                        "A few stretches of stale values made a sound model look broken."
                        if raw["mape"] >= 1.5 * test["mape"]
                        else "Stale values quietly degrade the evaluation."
                    ),
                }
            )
        titles[title] = {"name": name, "headline": headline, "bullets": bullets}

    return {
        "titles": titles,
        "next_steps": [
            "Join this with a live-ops calendar (patches, events, sales) so title-specific spikes get a cause, not just a flag.",
            "Segment by platform, region and player tenure, which Steam's public counts cannot provide.",
            "Track forecast error and interval coverage weekly, and recalibrate automatically when coverage drifts.",
            "Turn the weekly report into a scheduled job that writes the note and flags only what changed.",
        ],
    }
