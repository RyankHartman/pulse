-- Sanity check on the raw data: inside one snapshot, a lower-ranked title should never
-- have more concurrent players than the title ranked just above it.
with ordered as (
    select ts, rank, current_players,
           lag(current_players) over (partition by ts order by rank) as ccu_above
    from obs
)
select count(*) as violations
from ordered
where ccu_above is not null
  and current_players > ccu_above
