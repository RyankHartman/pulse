-- Do the minor defects spread across the whole file, or cluster?
-- Three different symptoms: duplicate rows, partly frozen snapshots, and rank order that
-- disagrees with player counts. If they share a time window, that is one collector
-- incident, not three unrelated problems.
with dup as (
    select ts from obs group by title, ts having count(*) > 1
),
partial as (
    select ts from snapshot_change where share_unchanged >= 0.15 and share_unchanged < 0.5
),
rank_bad as (
    select ts
    from (
        select ts, current_players,
               lag(current_players) over (partition by ts order by rank) as ccu_above
        from obs
    )
    where ccu_above is not null and current_players > ccu_above
)
select 'duplicate rows' as defect, count(*) as n, min(ts) as first_ts, max(ts) as last_ts from dup
union all
select 'partially frozen snapshots', count(*), min(ts), max(ts) from partial
union all
select 'rank-order violations', count(*), min(ts), max(ts) from rank_bad
