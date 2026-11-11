"""Run the whole pipeline and write the JSON the dashboard reads.

    python pipeline/fetch_data.py   # once
    python pipeline/build.py
"""
from __future__ import annotations

import time
from datetime import date

import anomalies
import cohorts
import forecast
import integrity
import summary
from common import daily_frame, write_json
from config import DATASET, FOCUS_TITLES, SHORT_NAMES
from load import SQL_DIR, connect


def main() -> None:
    started = time.time()
    con = connect()
    daily = daily_frame(con)
    daily_uncleaned = daily_frame(con, source="deduped")

    def step(label, fn):
        t = time.time()
        result = fn()
        print(f"  {label:<10} {time.time() - t:5.1f}s")
        return result

    print("Building Pulse data...")
    integ = step("integrity", lambda: integrity.build(con))
    fc = step("forecast", lambda: forecast.build(daily, daily_uncleaned))
    an = step("anomalies", lambda: anomalies.build(daily))
    co = step("cohorts", lambda: cohorts.build(con, daily))
    summ = summary.build(fc, an, integ)

    write_json("integrity", integ)
    write_json("forecast", fc)
    write_json("anomalies", an)
    write_json("cohorts", co)
    write_json("summary", summ)
    write_json("sql", {p.stem: p.read_text(encoding="utf-8").strip() for p in sorted(SQL_DIR.glob("*.sql"))})
    write_json(
        "meta",
        {
            "generated": date.today(),
            "dataset": DATASET,
            "titles": [{"title": t, "name": SHORT_NAMES.get(t, t)} for t in FOCUS_TITLES],
        },
    )
    print(f"Done in {time.time() - started:.1f}s.")


if __name__ == "__main__":
    main()
