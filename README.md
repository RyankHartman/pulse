# Pulse

**Engagement analytics on real data: can we trust it, what changed, and what happens next?**

Pulse takes a public dataset of hourly player counts for the Steam top 100 (May 2018 to March 2019) and does
what a product analyst does with a live game: check the data, forecast, explain the anomalies, and compare
launch cohorts. It ships as a SQL + Python pipeline that writes static JSON, and a small React dashboard on top.

**[Live dashboard](https://ryankhartman.github.io/pulse/)**

The point is the method, not the games. Swap the table and the same questions apply to any live product.

## The four questions

| # | Question | What Pulse does |
|---|----------|-----------------|
| 1 | **Can we trust the data?** | Checks coverage, duplicates, rank order, and, the one that mattered, **frozen feeds**: hours where every title repeats the previous hour's value. Row counts pass. Values are stale. |
| 2 | **What happens next?** | 14-day forecasts per title. Rolling-origin backtest, four candidate models, walk-forward model choice, calibrated 80% and 95% bands, scored against a "same weekday last week" baseline. |
| 3 | **What changed, and is it real?** | Robust STL residual z-score plus a 15% practical-significance floor. Each flag is classed as title-specific, platform-wide, or data-suspect, so you only chase what the product caused. |
| 4 | **Which launches stick?** | Kaplan-Meier survival of new titles in the top 100, with right-censoring. "Breakout" is defined from the first three days only, so it is knowable at launch. |

## Findings worth knowing

- **A frozen feed hid in complete-looking data.** On Jan 23, 2019 every title repeated its previous value for 19
  hours, and again for 18 hours on Mar 6. All 100 rows were present, so completeness checks passed. In total 54 hourly snapshots in 19 runs were
  stale. Left in, PUBG's 14-day forecast error was 17.7%. After cleaning it was 7.7% (baseline 9.9%).
- **The minor defects are one incident.** All 34 conflicting duplicate rows, 15 partly frozen snapshots and
  16 rank-order violations fall between Dec 7 and Dec 12, 2018. They are under 0.3% of the data. Duplicates are
  collapsed, the rest are documented as a limitation.
- **The simple baseline is hard to beat.** For several titles the weekday-profile baseline is within a point
  of the best model. Pulse says so rather than pretending the model adds value.
- **Not every band is trustworthy.** PUBG's 80% band covers 68% of scored days because the series got more
  volatile than the calibration period. Pulse reports this and recommends rolling recalibration.
- **Breakout launches stick.** 80% of breakout launches are still ranked at day 7 versus 44% of others.

Every number above is computed by the pipeline. None is typed in by hand.

## Honest limits

- Daily peak concurrent players is a proxy for engagement, not retention or revenue.
- The dataset has no patch, sale, or event calendar. Pulse can say a title-specific event happened, not why.
- Steam publishes no per-user data, so real user cohorts are impossible. The cohort view uses title cohorts.
- "Battle royale" launches are labeled by hand from title names (8 titles). It is a scorecard, not a statistic.
- About ten months of data, one platform, 2018 to 2019.

## Run it

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt     # on macOS/Linux: .venv/bin/pip
.venv/Scripts/python pipeline/fetch_data.py       # downloads 39 MB into data/raw/
.venv/Scripts/python pipeline/build.py            # about a minute; writes web/public/data/*.json
cd web && npm install && npm run dev              # http://localhost:5173
```

The cleaning logic is plain SQL in [`sql/`](sql), run by DuckDB directly on the CSV. The dashboard has a
"view the SQL" panel so the logic can be read without opening the repo.

## Layout

```
sql/        cleaning and analysis queries (DuckDB)
pipeline/   Python: forecasting, anomalies, cohorts, summaries, build
web/        Vite + React + TypeScript dashboard (static, reads web/public/data)
data/raw/   downloaded dataset (gitignored)
```

## Data and attribution

Dornekott, D. (2019). *The Top 100 Titles on Steam: May 2018 to March 2019.* Mendeley Data, V1.
doi:[10.17632/fc969vwptj.1](https://doi.org/10.17632/fc969vwptj.1). Licensed CC BY 4.0.
This project is not affiliated with or endorsed by Valve, Steam, or the dataset's author.

Summaries are deterministic templates filled from computed numbers. There is no LLM and no API key.
