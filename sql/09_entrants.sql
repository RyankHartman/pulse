-- Title lifetimes in the top 100. A title "enters" the first day it appears and
-- "exits" when it stops appearing. This is the closest honest analog to user
-- cohorts here: Steam exposes no per-user data, only title-level concurrency.
select
    title,
    min(day)                  as first_day,
    max(day)                  as last_day,
    count(distinct day)       as active_days,
    max(current_players)      as peak_ccu
from clean
group by title
order by first_day
