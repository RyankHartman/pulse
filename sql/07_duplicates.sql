-- Titles that appear more than once in the same hourly snapshot (raw data).
select
    title,
    ts,
    count(*)                as copies,
    min(rank)               as best_rank,
    max(rank)               as worst_rank,
    min(current_players)    as min_ccu,
    max(current_players)    as max_ccu,
    round(100.0 * (max(current_players) - min(current_players)) / max(current_players), 1) as gap_pct
from obs
group by title, ts
having count(*) > 1
order by ts
