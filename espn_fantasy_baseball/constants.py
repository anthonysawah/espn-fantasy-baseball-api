"""ESPN Fantasy Baseball constants: endpoints, slot/position/stat ID maps."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

FANTASY_READ_BASE = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/flb"
FANTASY_WRITE_BASE = "https://lm-api-writes.fantasy.espn.com/apis/v3/games/flb"
FANTASY_HISTORICAL_BASE = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/flb/leagueHistory"

# ESPN changed their API hostname over the years; current season uses the
# `lm-api-reads` host, while some legacy endpoints still respond on
# `fantasy.espn.com`.  We treat the read host as canonical.

# ---------------------------------------------------------------------------
# Roster lineup slots (the "slot" the player is currently in on a lineup)
# ---------------------------------------------------------------------------

LINEUP_SLOT_MAP: dict[int, str] = {
    0: "C",
    1: "1B",
    2: "2B",
    3: "3B",
    4: "SS",
    5: "OF",
    6: "2B/SS",
    7: "1B/3B",
    8: "LF",
    9: "CF",
    10: "RF",
    11: "DH",
    12: "UTIL",
    13: "P",
    14: "SP",
    15: "RP",
    16: "BE",
    17: "IL",
    18: "INV",   # Invalid
    19: "IF",    # Infielder (rare)
    20: "Bench",
    21: "IL",
}

# ---------------------------------------------------------------------------
# Eligible positions (a player's `eligibleSlots` come from the same space
# as LINEUP_SLOT_MAP – ESPN uses one unified slot-id space)
# ---------------------------------------------------------------------------

POSITION_MAP: dict[int, str] = {
    0: "C",
    1: "1B",
    2: "2B",
    3: "3B",
    4: "SS",
    5: "OF",
    6: "2B/SS",
    7: "1B/3B",
    8: "LF",
    9: "CF",
    10: "RF",
    11: "DH",
    12: "UTIL",
    13: "P",
    14: "SP",
    15: "RP",
}

# ---------------------------------------------------------------------------
# MLB Pro Teams.  ESPN's own pro-team ids (NOT MLB.com ids).
# ---------------------------------------------------------------------------

PRO_TEAM_MAP: dict[int, str] = {
    0: "FA",   # Free Agent
    1: "BAL",
    2: "BOS",
    3: "LAA",
    4: "CHW",
    5: "CLE",
    6: "DET",
    7: "KC",
    8: "MIL",
    9: "MIN",
    10: "NYY",
    11: "OAK",
    12: "SEA",
    13: "TEX",
    14: "TOR",
    15: "ATL",
    16: "CHC",
    17: "CIN",
    18: "HOU",
    19: "LAD",
    20: "WSH",
    21: "NYM",
    22: "PHI",
    23: "PIT",
    24: "STL",
    25: "SD",
    26: "SF",
    27: "COL",
    28: "MIA",
    29: "ARI",
    30: "TB",
}

# ---------------------------------------------------------------------------
# Stat IDs.  ESPN's stat ids, keyed on the string ids returned in JSON
# (they come back as string keys inside `stats[*].stats`).
# ---------------------------------------------------------------------------

STAT_ID_MAP: dict[int, str] = {
    # ---- Batting ----
    0: "AB",
    1: "H",
    2: "AVG",
    3: "2B",
    4: "3B",
    5: "HR",
    6: "XBH",
    7: "TB",
    8: "SLG",
    9: "1B",
    10: "BB",
    11: "IBB",
    12: "HBP",
    13: "SF",
    14: "SH",
    15: "SAC",
    16: "PA",
    17: "OBP",
    18: "OPS",
    19: "wOBA",
    20: "R",
    21: "RBI",
    22: "GIDP",
    23: "SO",
    24: "PO",
    25: "A",
    26: "OFA",
    27: "FPCT",
    28: "SB",
    29: "CS",
    30: "SBN",
    31: "GP",
    32: "GS",
    # ---- Pitching ----
    33: "W",
    34: "L",
    35: "WPCT",
    36: "SV",
    37: "BSV",
    38: "GS_P",
    39: "CG",
    40: "QS",
    41: "SHO",
    42: "GF",
    43: "IP",
    44: "OUTS",
    45: "BF",
    46: "PIT",
    47: "HA",
    48: "RA",
    49: "ER",
    50: "BBI",
    51: "IBBI",
    52: "HBPP",
    53: "K",
    54: "AVGA",
    55: "HRA",
    56: "OBPA",
    57: "SLGA",
    58: "OPSA",
    59: "ERA",
    60: "WHIP",
    61: "K/BB",
    62: "K/9",
    63: "SOPCT",
    64: "WP",
    65: "BK",
    66: "SVOP",
    67: "HLD",
    # ---- Game state / roster / misc ----
    99: "STARTER",
}

# Stat period ids returned in each `stats` entry's `statSourceId`/`statSplitTypeId`
STAT_SOURCE = {0: "real", 1: "projected"}
STAT_SPLIT = {0: "season", 1: "last_7", 2: "last_15", 3: "last_30", 5: "date_range"}

# ---------------------------------------------------------------------------
# Injury status
# ---------------------------------------------------------------------------

INJURY_STATUS_MAP: dict[str, str] = {
    "ACTIVE": "Active",
    "BEREAVEMENT": "Bereavement",
    "DAY_TO_DAY": "Day-to-Day",
    "FIFTEEN_DAY_DL": "15-Day IL",
    "SIXTY_DAY_DL": "60-Day IL",
    "SEVEN_DAY_DL": "7-Day IL",
    "TEN_DAY_DL": "10-Day IL",
    "DL": "IL",
    "OUT": "Out",
    "PATERNITY": "Paternity",
    "SUSPENSION": "Suspension",
    "PERSONAL": "Personal",
}

# ---------------------------------------------------------------------------
# Transaction types (ESPN "activity" objects)
# ---------------------------------------------------------------------------

ACTIVITY_MAP: dict[int, str] = {
    178: "FA ADDED",
    179: "WAIVER ADDED",
    180: "DROPPED",
    181: "DROPPED",
    188: "LINEUP",
    239: "DROPPED",
    244: "TRADED",
}

# ---------------------------------------------------------------------------
# Views.  The `view` query parameter composes what ESPN returns.
# ---------------------------------------------------------------------------

VIEW_TEAM = "mTeam"
VIEW_ROSTER = "mRoster"
VIEW_MATCHUP = "mMatchup"
VIEW_MATCHUP_SCORE = "mMatchupScore"
VIEW_BOXSCORE = "mBoxscore"
VIEW_SETTINGS = "mSettings"
VIEW_SCHEDULE = "mSchedule"
VIEW_STANDINGS = "mStandings"
VIEW_PLAYER = "mPlayer"
VIEW_TRANSACTIONS = "mTransactions2"
VIEW_DRAFT = "mDraftDetail"
VIEW_TOPICS = "kona_player_info"

# Default user agent for requests — some ESPN endpoints 403 without one.
DEFAULT_USER_AGENT = (
    "espn-fantasy-baseball-api/0.1 (+https://github.com/anthonysawah/espn-fantasy-baseball-api)"
)
