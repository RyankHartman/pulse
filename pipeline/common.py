"""Helpers shared by the analysis modules."""
from __future__ import annotations

import json
import math
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from config import MIN_HOURS_FOR_DAY, OUT_DIR, WINDOW_END, WINDOW_START
from load import read_sql


def jsonable(obj):
    """Recursively convert numpy / pandas / date values so json.dump never emits NaN."""
    if isinstance(obj, dict):
        return {str(k): jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [jsonable(v) for v in obj]
    if isinstance(obj, (pd.Timestamp, datetime)):
        return obj.date().isoformat() if obj.hour == 0 and obj.minute == 0 else obj.isoformat(timespec="minutes")
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        value = float(obj)
        return None if math.isnan(value) or math.isinf(value) else value
    if obj is pd.NaT:
        return None
    return obj


def write_json(name: str, payload) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{name}.json"
    path.write_text(json.dumps(jsonable(payload), separators=(",", ":"), allow_nan=False), encoding="utf-8")
    return path


def daily_frame(con, source: str = "clean") -> pd.DataFrame:
    """Daily peak per title (04_daily_series.sql). `source` picks the view it reads from:
    "clean" is the real pipeline, "deduped" skips frozen-feed removal for the what-if comparison."""
    df = con.execute(read_sql("04_daily_series").replace("from clean", f"from {source}")).fetchdf()
    df["day"] = pd.to_datetime(df["day"])
    return df


def title_series(daily: pd.DataFrame, title: str) -> pd.DataFrame:
    """Contiguous daily frame for one title with explicit gap flags.

    Columns: peak (NaN where unusable), hours, usable (bool).
    A day is usable only if it has at least MIN_HOURS_FOR_DAY hourly snapshots.
    """
    index = pd.date_range(WINDOW_START, WINDOW_END, freq="D")
    sub = daily[daily["title"] == title].set_index("day").reindex(index)
    sub["hours"] = sub["hours_observed"].fillna(0).astype(int)
    sub["usable"] = (sub["hours"] >= MIN_HOURS_FOR_DAY) & sub["daily_peak"].notna()
    sub["peak"] = sub["daily_peak"].where(sub["usable"])
    return sub[["peak", "hours", "usable"]]


def impute_log(peak: pd.Series) -> pd.Series:
    """Log-scale series with unusable days filled by linear interpolation (for model fitting only)."""
    logged = np.log(peak)
    return logged.interpolate(limit_direction="both")
