# API reference

Everything is importable directly from the top-level package:

```python
from espn_fantasy_baseball import (
    League, ESPNClient,
    Team, Player, PlayerStats,
    Matchup, Boxscore, BoxscorePlayer,
    DraftPick, Activity, ActivityAction,
    LeagueSettings, ScoringItem,
    # exceptions
    ESPNFantasyError, ESPNAPIError,
    AuthenticationError, PrivateLeagueError,
    LeagueNotFoundError, InvalidSeasonError,
)
```

---

## `League`

The main entry point. Construct it once per `(league_id, season)`.

### Constructor

```python
League(
    league_id: int,
    year: int,
    *,
    espn_s2: str | None = None,
    swid: str | None = None,
    client: ESPNClient | None = None,
    **client_kwargs,
)
```

| Argument | Meaning |
| --- | --- |
| `league_id` | The numeric league id (from your league's URL). |
| `year` | The fantasy season, e.g. `2024`. |
| `espn_s2`, `swid` | Auth cookies for private leagues. |
| `client` | Pre-built `ESPNClient` (overrides the other args). |
| `**client_kwargs` | Forwarded to `ESPNClient` (e.g. `timeout`, `max_retries`, `session`, `user_agent`). |

### Methods

| Method | Returns | Notes |
| --- | --- | --- |
| `settings()` | `LeagueSettings` | Name, size, scoring, roster slots. |
| `teams()` | `list[Team]` | In the order ESPN returns them. |
| `team(team_id)` | `Team` | Raises `KeyError` if not found. |
| `standings()` | `list[Team]` | Sorted by win-pct (desc), then points-for (desc). |
| `schedule()` | `list[Matchup]` | Full season schedule. |
| `matchups(period)` | `list[Matchup]` | Just the given matchup period. |
| `scoreboard(period=None)` | `list[Matchup]` | Defaults to ESPN's current matchup period. |
| `boxscores(period)` | `list[Boxscore]` | Matchups plus per-player stats. |
| `draft()` | `list[DraftPick]` | In overall-pick order. |
| `free_agents(size=50, position=None, sort_by="percent_owned", scoring_period=None)` | `list[Player]` | See [sort keys](#free-agent-sort-keys). |
| `player_by_id(player_id)` | `Player \| None` | `None` if not found. |
| `recent_activity(size=25)` | `list[Activity]` | Adds / drops / trades feed. |
| `power_rankings(weights=None)` | `list[tuple[Team, float]]` | Blended score, high first. |
| `refresh()` | `None` | Drop the in-process cache. |

Property `league_id`, `year`, and `client` give access to the underlying
configuration. All returned JSON is stashed on each resource as `.raw`.

#### Free agent sort keys

| `sort_by` | What it sorts by |
| --- | --- |
| `"percent_owned"` (default) | ESPN's `%Rostered`. |
| `"percent_started"` | ESPN's `%Started`. |
| `"season_points"` | Applied season total. |
| `"last7_points"` | Applied points over the last 7 days. |

#### `power_rankings(weights=...)`

The default formula is:

```
score = 0.7 * points_for + 0.3 * win_pct * max(points_for across league)
```

Override with `weights={"points_for": 0.65, "win_pct": 0.35}`. Other
keys are ignored.

---

## `ESPNClient`

The HTTP layer. You rarely construct this directly — `League` does it
for you — but it's useful for testing or exotic cases.

### Constructor

```python
ESPNClient(
    league_id: int,
    year: int,
    *,
    espn_s2: str | None = None,
    swid: str | None = None,
    session: requests.Session | None = None,
    timeout: float = 30.0,
    max_retries: int = 3,
    user_agent: str = DEFAULT_USER_AGENT,
)
```

### Methods

| Method | Purpose |
| --- | --- |
| `url()` | Base URL for this season (current vs. history). |
| `get(*, views=None, params=None, headers=None, path="")` | Issue a GET. |

`get()` composes one or more `view=` query params, attaches auth
cookies, retries on 429/5xx with exponential backoff, and raises the
typed exceptions described below.

---

## Resources

### `Team`

```python
@dataclass
class Team:
    id: int
    abbreviation: str
    name: str
    owner_ids: list[str]
    owner_names: list[str]
    logo_url: str | None
    division_id: int | None
    wins: int
    losses: int
    ties: int
    points_for: float
    points_against: float
    playoff_seed: int | None
    standings_rank: int | None
    waiver_rank: int | None
    moves: int
    trades: int
    acquisition_budget_spent: int
    roster: list[Player]
    raw: Mapping[str, Any]
```

**Computed:**
- `team.record` — `"12-5-1"` (ties omitted when zero).
- `team.starters()` — `list[Player]` on active lineup slots.
- `team.bench()` — `list[Player]` on bench.
- `team.injured()` — `list[Player]` on the IL.

### `Player` / `PlayerStats`

```python
@dataclass
class Player:
    id: int
    name: str
    pro_team: str
    eligible_positions: list[str]
    lineup_slot: str | None
    injury_status: str | None
    active_status: str | None
    acquisition_type: str | None    # DRAFT, FA, WAIVER, TRADE
    percent_owned: float
    percent_started: float
    stats: list[PlayerStats]
    raw: Mapping[str, Any]

@dataclass
class PlayerStats:
    season: int
    source: str       # "real" | "projected"
    split: str        # "season" | "last_7" | "last_15" | "last_30" | "date_range"
    stats: dict[str, float]
    applied_total: float
```

**Helpers:**
- `player.season_stats(year=None, projected=False)` → `dict[str, float]`
  with decoded stat names.
- `player.is_pitcher()`, `player.is_batter()`.

### `Matchup`

```python
@dataclass
class Matchup:
    matchup_period: int
    matchup_id: int
    playoff_tier: str | None
    winner: str | None        # "HOME" | "AWAY" | "TIE" | None
    home_team_id: int | None
    away_team_id: int | None
    home_score: float
    away_score: float
    home_projected: float | None
    away_projected: float | None
    raw: Mapping[str, Any]
```

### `Boxscore` / `BoxscorePlayer`

Same shape as `Matchup` but with full lineups attached:

```python
@dataclass
class Boxscore:
    matchup_period: int
    matchup_id: int
    home_team_id: int | None
    away_team_id: int | None
    home_score: float
    away_score: float
    home_lineup: list[BoxscorePlayer]
    away_lineup: list[BoxscorePlayer]

@dataclass
class BoxscorePlayer:
    player: Player
    lineup_slot: str | None
    points: float
    stats: dict[str, float]
```

`box.winner()` → `"HOME" | "AWAY" | "TIE" | None`.

### `DraftPick`

```python
@dataclass
class DraftPick:
    overall_pick: int
    round: int
    round_pick: int
    team_id: int
    player_id: int
    player_name: str | None
    bid_amount: int | None       # auction leagues
    keeper: bool
    auto_drafted: bool
    nominating_team_id: int | None
```

### `Activity` / `ActivityAction`

```python
@dataclass
class Activity:
    id: str
    date: datetime | None
    type: str                 # "ADDED" | "DROPPED" | "TRADE" | "ADD/DROP" | ...
    actions: list[ActivityAction]

@dataclass
class ActivityAction:
    type: str
    team_id: int | None
    player_id: int
    player_name: str | None
    bid_amount: int | None
```

### `LeagueSettings` / `ScoringItem`

```python
@dataclass
class LeagueSettings:
    name: str
    season: int
    size: int
    scoring_type: str          # "H2H_POINTS", "H2H_CATEGORY", "ROTO", "POINTS", ...
    playoff_teams: int
    regular_season_matchup_periods: int
    trade_deadline: int | None
    roster_slots: dict[str, int]
    scoring: list[ScoringItem]
    tie_rule: str | None
    acquisition_budget: int | None
    uses_waiver: bool

@dataclass
class ScoringItem:
    stat_id: int
    stat_name: str
    points: float
    is_reverse: bool
```

---

## Exceptions

All inherit from `ESPNFantasyError`:

```
ESPNFantasyError
├── ESPNAPIError          non-2xx responses / parse errors
└── AuthenticationError
    └── PrivateLeagueError  401/403 — usually missing/expired cookies
├── LeagueNotFoundError   404
└── InvalidSeasonError    400 — unsupported season
```

`ESPNAPIError` carries `status_code` and `response_text` attributes.

---

## Constants

Importable from `espn_fantasy_baseball.constants`:

| Constant | Contents |
| --- | --- |
| `STAT_ID_MAP` | `{stat_id: abbrev}` for batting + pitching stats. |
| `POSITION_MAP`, `LINEUP_SLOT_MAP` | `{slot_id: abbrev}`. |
| `PRO_TEAM_MAP` | `{pro_team_id: team_abbrev}`. |
| `INJURY_STATUS_MAP` | ESPN enum → pretty string. |
| `ACTIVITY_MAP` | `{msg_type: label}`. |
| `VIEW_*` | The string constants for ESPN's `view` query param. |
| `FANTASY_READ_BASE`, `FANTASY_HISTORICAL_BASE` | Base URLs. |
