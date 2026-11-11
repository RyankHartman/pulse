-- Step 1 of cleaning: collapse duplicate rows so every (title, hour) is counted once.
--
-- A title can appear twice in one hourly snapshot at nearby ranks with different
-- player counts, which looks like the leaderboard shifting between paged requests.
-- We cannot know which reading is right, so keep the best-ranked row and report
-- how many rows this affected (see 07_duplicates.sql).
create or replace view deduped as
select title, current_players, peak_players, hours_played, hour, day, rank, ts
from obs
qualify row_number() over (partition by title, ts order by rank, current_players desc) = 1
