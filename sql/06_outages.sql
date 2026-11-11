-- Gaps-and-islands again: group consecutive untrustworthy hours into outages.
-- A run can be a true collection outage or a frozen feed, and the report tells them apart
-- by checking the run against the frozen snapshots from 03_stale_runs.sql.
with expected as (
    select unnest(generate_series(
        timestamp '2018-05-11 00:00', timestamp '2019-03-14 23:00', interval 1 hour
    )) as ts
),
missing as (
    select e.ts
    from expected e
    left join (select distinct ts from clean) s using (ts)
    where s.ts is null
),
islands as (
    select ts, ts - row_number() over (order by ts) * interval 1 hour as run_key
    from missing
)
select min(ts) as outage_start, max(ts) as outage_end, count(*) as missing_hours
from islands
group by run_key
order by missing_hours desc
