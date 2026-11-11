-- Group consecutive frozen hours into runs (gaps-and-islands).
-- Subtracting a running row number from each hour gives every unbroken run the same
-- key, so one GROUP BY turns a run of hours into one row.
with islands as (
    select ts, ts - row_number() over (order by ts) * interval 1 hour as run_key
    from stale_snapshots
)
select min(ts) as run_start, max(ts) as run_end, count(*) as frozen_hours
from islands
group by run_key
order by frozen_hours desc, run_start
