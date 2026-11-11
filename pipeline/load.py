"""Load the raw Steam CSV into DuckDB with an explicit schema.

DuckDB's CSV auto-detection misreads this file (it decides there is no quote
character, so titles like "Warhammer 40,000: Inquisitor - Martyr" split at the
comma), so the schema and quoting are spelled out here.
"""
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
RAW_CSV = ROOT / "data" / "raw" / "steam_data.csv"
SQL_DIR = ROOT / "sql"

SCHEMA = (
    "{'title':'VARCHAR','current_players':'BIGINT','peak_players':'BIGINT',"
    "'hours_played':'BIGINT','hour':'INTEGER','day':'DATE','rank':'INTEGER'}"
)


def connect() -> duckdb.DuckDBPyConnection:
    if not RAW_CSV.exists():
        raise FileNotFoundError(f"{RAW_CSV} not found. Run: python pipeline/fetch_data.py")
    con = duckdb.connect()
    con.execute(
        f"""
        create or replace view obs as
        select
            title,
            current_players,
            peak_players,
            hours_played,
            hour,
            day,
            rank,
            (day + hour * interval 1 hour) as ts
        from read_csv('{RAW_CSV.as_posix()}',
                      header = true, quote = '"', escape = '"',
                      columns = {SCHEMA})
        """
    )
    for script in ("00_dedupe", "01_stale_snapshots", "02_clean"):
        for statement in read_sql(script).split(";"):
            if statement.strip():
                con.execute(statement)
    return con


def read_sql(name: str) -> str:
    """Return the text of sql/<name>.sql so the same query is run and displayed."""
    return (SQL_DIR / f"{name}.sql").read_text(encoding="utf-8").strip()
