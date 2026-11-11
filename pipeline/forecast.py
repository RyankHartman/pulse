"""Backtested 14-day forecasts of daily peak concurrent players, with calibrated intervals.

The point of this module is not a clever model, it is being able to defend the numbers:

* three simple models compete in a rolling-origin backtest
* the model and the interval widths are chosen using only data that was available then
* the intervals are then checked out of sample: did the "80%" band really contain ~80%?
"""
from __future__ import annotations

import warnings
from datetime import date

import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from common import impute_log, title_series
from config import DAMPING, EVAL_SPLIT, FOCUS_TITLES, HORIZON, MIN_TRAIN_DAYS, ORIGIN_STEP, SHORT_NAMES

H = HORIZON
BUCKETS = [(0, 3), (3, 7), (7, 14)]  # horizon groups that share interval widths

MODEL_LABELS = {
    "seasonal_naive": "Same weekday last week",
    "ets": "Damped-trend exponential smoothing",
    "weekday_drift": "Weekday profile + damped drift",
    "average": "Average of the three",
}


# --- models (all work on log daily peak) --------------------------------------
def f_seasonal_naive(y: np.ndarray, dates: pd.DatetimeIndex, h: int) -> np.ndarray:
    last_week = y[-7:]
    return np.array([last_week[k % 7] for k in range(h)])


def f_ets(y: np.ndarray, dates: pd.DatetimeIndex, h: int) -> np.ndarray:
    train = y[-180:]
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fit = ExponentialSmoothing(
                train,
                trend="add",
                damped_trend=True,
                seasonal="add",
                seasonal_periods=7,
                initialization_method="estimated",
            ).fit(optimized=True)
            out = np.asarray(fit.forecast(h))
        if not np.all(np.isfinite(out)):
            raise ValueError("non-finite forecast")
        return out
    except Exception:  # fall back rather than lose an origin
        return f_seasonal_naive(y, dates, h)


def f_weekday_drift(y: np.ndarray, dates: pd.DatetimeIndex, h: int) -> np.ndarray:
    m1, m0 = y[-7:].mean(), y[-14:-7].mean()
    slope = (m1 - m0) / 7
    level = m1 + 3 * slope  # a trailing 7-day mean is centred three days back
    block = y[-28:].reshape(4, 7)
    resid = block - block.mean(axis=1, keepdims=True)
    dow = dates[-28:].dayofweek.to_numpy().reshape(4, 7)
    profile = {wd: float(resid[dow == wd].mean()) for wd in range(7)}
    out, cumulative = [], 0.0
    for k in range(1, h + 1):
        cumulative += DAMPING**k
        weekday = (dates[-1] + pd.Timedelta(days=k)).dayofweek
        out.append(level + slope * cumulative + profile[weekday])
    return np.array(out)


def f_average(y: np.ndarray, dates: pd.DatetimeIndex, h: int) -> np.ndarray:
    return np.mean(
        [f_seasonal_naive(y, dates, h), f_ets(y, dates, h), f_weekday_drift(y, dates, h)], axis=0
    )


MODELS = {
    "seasonal_naive": f_seasonal_naive,
    "ets": f_ets,
    "weekday_drift": f_weekday_drift,
    "average": f_average,
}


# --- backtesting --------------------------------------------------------------
def run_backtest(y_log, truth_log, dates, origins):
    """For every forecast origin, forecast H days with every model.

    Returns signed log errors, log predictions and the realised log values, each shaped
    (n_origins, H). Errors are NaN where the realised day was unusable (not observed).
    """
    n = len(origins)
    preds = {m: np.full((n, H), np.nan) for m in MODELS}
    actual = np.full((n, H), np.nan)
    for r, i in enumerate(origins):
        train, train_dates = y_log[: i + 1], dates[: i + 1]
        actual[r] = truth_log[i + 1 : i + 1 + H]
        for name, fn in MODELS.items():
            preds[name][r] = fn(train, train_dates, H)
    errors = {m: actual - preds[m] for m in MODELS}
    return errors, preds, actual


def choose_and_calibrate(errors, mask):
    """Pick the model with the lowest mean absolute log error on `mask` origins, and take
    empirical error quantiles (per horizon bucket) as its prediction-interval offsets."""
    scores = {m: float(np.nanmean(np.abs(e[mask]))) for m, e in errors.items()}
    best = min(scores, key=scores.get)
    e = errors[best][mask]
    offsets = np.zeros((H, 4))  # lo80, hi80, lo95, hi95 (log offsets added to the forecast)
    for a, b in BUCKETS:
        vals = e[:, a:b].ravel()
        vals = vals[~np.isnan(vals)]
        offsets[a:b] = np.quantile(vals, [0.10, 0.90, 0.025, 0.975])
    return best, scores, offsets


def level_mape(pred_log, actual_log, mask) -> float:
    pred, act = np.exp(pred_log[mask]), np.exp(actual_log[mask])
    return float(np.nanmean(np.abs(pred - act) / act))


def interval_rows(day_index, pred_log, offsets, actuals=None):
    rows = []
    for k in range(H):
        row = {
            "day": day_index[k],
            "mid": float(np.exp(pred_log[k])),
            "lo80": float(np.exp(pred_log[k] + offsets[k, 0])),
            "hi80": float(np.exp(pred_log[k] + offsets[k, 1])),
            "lo95": float(np.exp(pred_log[k] + offsets[k, 2])),
            "hi95": float(np.exp(pred_log[k] + offsets[k, 3])),
        }
        if actuals is not None:
            value = actuals[k]
            row["actual"] = None if np.isnan(value) else float(np.exp(value))
        rows.append(row)
    return rows


# --- per-title driver ---------------------------------------------------------
def forecast_title(daily: pd.DataFrame, title: str) -> dict:
    series = title_series(daily, title)
    usable = series["usable"]
    series = series.loc[usable.idxmax() : usable[::-1].idxmax()]  # trim partial edge days
    dates = series.index
    y_log = impute_log(series["peak"]).to_numpy()
    truth_log = np.log(series["peak"]).to_numpy()
    n = len(series)

    # Weekly origins, aligned so the last one is exactly the holdout cutoff (n - 1 - H).
    origins = list(range(n - 1 - H, MIN_TRAIN_DAYS - 2, -ORIGIN_STEP))[::-1]
    origin_dates = np.array([dates[i] for i in origins], dtype="datetime64[ns]")
    errors, preds, actual = run_backtest(y_log, truth_log, dates, origins)
    origin_idx = np.array(origins)

    # 1) Walk-forward evaluation. For every test origin we pick the model and calibrate the
    #    intervals using only forecasts whose 14-day window had already finished by then,
    #    exactly as it would run live, then score that origin against what really happened.
    split = np.datetime64(pd.Timestamp(EVAL_SPLIT))
    window_end = origin_dates + np.timedelta64(H, "D")
    test_mask = origin_dates > split
    chosen_log = np.full((len(origins), H), np.nan)
    chosen_by_origin = {}
    inside80 = inside95 = scored = 0
    for r in np.where(test_mask)[0]:
        past = window_end <= origin_dates[r]
        best_r, _, off_r = choose_and_calibrate(errors, past)
        chosen_by_origin[str(pd.Timestamp(origin_dates[r]).date())] = best_r
        chosen_log[r] = preds[best_r][r]
        e = errors[best_r][r]
        ok = ~np.isnan(e)
        inside80 += int((((e >= off_r[:, 0]) & (e <= off_r[:, 1])) & ok).sum())
        inside95 += int((((e >= off_r[:, 2]) & (e <= off_r[:, 3])) & ok).sum())
        scored += int(ok.sum())
    cov80, cov95 = inside80 / scored, inside95 / scored
    mape_test = level_mape(chosen_log, actual, test_mask)
    naive_test = level_mape(preds["seasonal_naive"], actual, test_mask)
    picks = list(chosen_by_origin.values())
    modal_pick = max(set(picks), key=picks.count)

    by_horizon = []
    for k in range(H):
        chosen = np.exp(chosen_log[test_mask][:, k])
        naive = np.exp(preds["seasonal_naive"][test_mask][:, k])
        real = np.exp(actual[test_mask][:, k])
        by_horizon.append(
            {
                "h": k + 1,
                "model": float(np.nanmean(np.abs(chosen - real) / real)),
                "naive": float(np.nanmean(np.abs(naive - real) / real)),
            }
        )

    models_table = []
    all_mask = np.ones(len(origins), dtype=bool)
    for m in MODELS:
        models_table.append(
            {
                "key": m,
                "label": MODEL_LABELS[m],
                "mape_all": level_mape(preds[m], actual, all_mask),
                "mape_test": level_mape(preds[m], actual, test_mask),
                "chosen": m == modal_pick,
            }
        )
    best_eval = modal_pick
    first_test = origin_dates[test_mask].min()
    calibration_origins = int((window_end <= first_test).sum())

    # 2) Holdout view: forecast the last H days from data that ends H days earlier.
    cutoff = n - 1 - H
    display_mask = (origin_idx + H) <= cutoff
    best_show, _, off_show = choose_and_calibrate(errors, display_mask)
    show_pred = MODELS[best_show](y_log[: cutoff + 1], dates[: cutoff + 1], H)
    holdout_days = [dates[cutoff + 1 + k] for k in range(H)]
    holdout = {
        "cutoff": dates[cutoff],
        "model": best_show,
        "model_label": MODEL_LABELS[best_show],
        "forecast": interval_rows(holdout_days, show_pred, off_show, truth_log[cutoff + 1 : cutoff + 1 + H]),
    }

    # 3) Projection past the end of the data, from everything we have.
    best_all, _, off_all = choose_and_calibrate(errors, np.ones(len(origins), dtype=bool))
    proj_pred = MODELS[best_all](y_log, dates, H)
    proj_days = [dates[-1] + pd.Timedelta(days=k + 1) for k in range(H)]
    projection = {
        "model": best_all,
        "model_label": MODEL_LABELS[best_all],
        "forecast": interval_rows(proj_days, proj_pred, off_all),
    }

    peaks = series["peak"].dropna()
    first28, last28 = float(peaks.iloc[:28].mean()), float(peaks.iloc[-28:].mean())

    return {
        "title": title,
        "name": SHORT_NAMES.get(title, title),
        "series": [
            {"day": d, "peak": None if np.isnan(p) else float(p), "usable": bool(u), "hours": int(hrs)}
            for d, (p, u, hrs) in zip(dates, zip(series["peak"], series["usable"], series["hours"]))
        ],
        "imputed_days": int((~series["usable"]).sum()),
        "trend": {"first28": first28, "last28": last28, "change_pct": 100 * (last28 / first28 - 1)},
        "holdout": holdout,
        "projection": projection,
        "backtest": {
            "origins": int(len(origins)),
            "calibration_origins": calibration_origins,
            "test_origins": int(test_mask.sum()),
            "calibration_end": EVAL_SPLIT,
            "models": models_table,
            "chosen_model": best_eval,
            "chosen_label": MODEL_LABELS[best_eval],
            "test": {
                "days_scored": scored,
                "picks": chosen_by_origin,
                "mape": mape_test,
                "naive_mape": naive_test,
                "skill_vs_naive": 1 - mape_test / naive_test,
                "coverage80": cov80,
                "coverage95": cov95,
            },
            "by_horizon": by_horizon,
        },
    }


def build(daily: pd.DataFrame, daily_uncleaned: pd.DataFrame) -> dict:
    """`daily_uncleaned` skips frozen-feed removal. Running the identical method on it shows
    what the data-integrity step is worth."""
    titles = {}
    for t in FOCUS_TITLES:
        result = forecast_title(daily, t)
        raw_test = forecast_title(daily_uncleaned, t)["backtest"]["test"]
        result["without_cleaning"] = {
            k: raw_test[k] for k in ("mape", "naive_mape", "skill_vs_naive", "coverage80", "coverage95")
        }
        titles[t] = result
    return {"horizon": H, "models": MODEL_LABELS, "titles": titles}
