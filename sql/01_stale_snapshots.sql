-- Step 2 of cleaning: find frozen snapshots.
--
-- Row-count checks pass on these (all 100 titles are present) but the values are stale:
-- the collector kept returning the previous hour's numbers. In a healthy hour almost
-- every title's player count changes, so the share of titles whose count is IDENTICAL
-- to their previous reading is near zero (median 0%, 99% of snapshots under 2%).
-- A snapshot where half or more of the titles are unchanged is treated as frozen.
create or replace view snapshot_change as
select ts, avg((current_players = previous_ccu)::int) as share_unchanged
from (
    select ts, title, current_players,
           lag(current_players) over (partition by title order by ts) as previous_ccu
    from deduped
)
where previous_ccu is not null
group by ts;

create or replace view stale_snapshots as
select ts, share_unchanged
from snapshot_change
where share_unchanged >= 0.5
