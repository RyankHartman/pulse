-- Which hourly snapshots survived cleaning, against every hour in the collection window?
-- Result: one row per hour, with present = false where we have nothing we can trust
-- (never collected, or collected but frozen).
with expected as (
    select unnest(generate_series(
        timestamp '2018-05-11 00:00', timestamp '2019-03-14 23:00', interval 1 hour
    )) as ts
),
seen as (select distinct ts from clean)
select e.ts, (s.ts is not null) as present
from expected e
left join seen s using (ts)
order by e.ts
