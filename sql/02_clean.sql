-- Step 3 of cleaning: drop frozen snapshots. Everything downstream reads this view.
-- Frozen hours are treated as MISSING, never as real readings and never as zero.
create or replace view clean as
select d.title, d.current_players, d.peak_players, d.hours_played, d.hour, d.day, d.rank, d.ts
from deduped d
left join stale_snapshots s using (ts)
where s.ts is null
