"""Shared constants for the Pulse pipeline."""
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "web" / "public" / "data"

DATASET = {
    "title": "The Top 100 Titles on Steam: May 2018 to March 2019",
    "author": "David Dornekott",
    "doi": "10.17632/fc969vwptj.1",
    "url": "https://data.mendeley.com/datasets/fc969vwptj/1",
    "license": "CC BY 4.0",
    "file": "steam_data.csv",
    "download_url": "https://data.mendeley.com/public-files/datasets/fc969vwptj/files/"
    "b701b9f4-7d91-4e0f-b293-9bd86679ec95/file_downloaded",
    "bytes": 38_994_420,
}

# Collection window, from the dataset description and the observed first/last snapshot.
WINDOW_START = date(2018, 5, 11)
WINDOW_END = date(2019, 3, 14)

# A day counts as fully observed only if most of its 24 hourly snapshots exist. The daily
# peak of a day with big holes may simply have missed the real peak hour.
MIN_HOURS_FOR_DAY = 20

# Shooter / battle-royale titles that are present in (almost) every snapshot.
FOCUS_TITLES = [
    "PLAYERUNKNOWN'S BATTLEGROUNDS",
    "Counter-Strike: Global Offensive",
    "Tom Clancy's Rainbow Six Siege",
    "Team Fortress 2",
    "Paladins",
    "Warframe",
]
SHORT_NAMES = {
    "PLAYERUNKNOWN'S BATTLEGROUNDS": "PUBG",
    "Counter-Strike: Global Offensive": "CS:GO",
    "Tom Clancy's Rainbow Six Siege": "Rainbow Six Siege",
    "Team Fortress 2": "Team Fortress 2",
    "Paladins": "Paladins",
    "Warframe": "Warframe",
}

# Battle-royale launches, labelled by hand from the titles themselves.
BR_ENTRANTS = [
    "Rules Of Survival",
    "Totally Accurate Battlegrounds",
    "Realm Royale",
    "Cuisine Royale",
    "Islands of Nyne: Battle Royale",
    "Ring of Elysium",
    "Battlerite Royale",
    "Z1 Battle Royale",
]

# Forecasting
HORIZON = 14
MIN_TRAIN_DAYS = 90
ORIGIN_STEP = 7
EVAL_SPLIT = date(2018, 12, 31)  # calibrate on origins ending before this, test after
DAMPING = 0.9

# Anomalies: an event must be statistically extreme AND big enough for a PM to care about.
ANOMALY_Z = 3.5
ANOMALY_MIN_PCT = 15
PLATFORM_Z = 2.5
PLATFORM_SHARE = 0.35

# Cohorts
ENTRANT_AFTER = date(2018, 6, 1)  # first seen after this => a genuine entrant, not an incumbent
EXIT_GAP_DAYS = 3  # last seen at least this many days before the window end => it exited
BREAKOUT_EARLY_PEAK = 15_000  # peak daily CCU in the first three days, which is knowable at launch
