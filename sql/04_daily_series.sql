-- One row per title per day, from the cleaned snapshots.
--   daily_peak     = the highest hourly concurrent-player (CCU) reading that day
--   hours_observed = how many of the day's 24 hourly snapshots survived cleaning
--
-- Daily peak is used (not the daily mean) because it is robust to the top-100
-- cutoff: a title can drop out of the list at its quiet overnight hours, but its
-- peak hour sits far above the cutoff.
select
    title,
    day,
    max(current_players)  as daily_peak,
    count(distinct hour)  as hours_observed
from clean
group by title, day
order by title, day
