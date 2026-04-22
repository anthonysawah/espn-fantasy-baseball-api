# espn-fantasy-baseball-api

A modern, typed, friendly Python client for the **ESPN Fantasy Baseball** API.

> ESPN's Fantasy API is undocumented. This library reverse-engineers the
> public endpoints the espn.com UI uses, decodes ESPN's numeric slot/stat/
> position ids into human-readable names, and gives you real dataclasses for
> leagues, teams, players, matchups, boxscores, drafts, transactions, and
> settings.

## Features

- **Read the whole league** — settings, standings, schedules, matchups,
  boxscores, rosters, drafts, free agents, transactions, activity feed.
- **Authentication for private leagues** via `espn_s2` / `SWID` cookies.
- **Decoded everything** — no more `stats["5"]`, you get `stats["HR"]`.
- **Lazy + cached** — calls are only issued when you ask, and repeated
  reads in the same `League` instance are served from an in-process cache.
- **Built-in retries** for ESPN's occasional 5xx/rate-limit hiccups.
- **Zero heavy deps** — just `requests`.
- **CLI** — `espn-fb standings --league 123456 --year 2024`.
- **Works offline in tests** — the HTTP layer is a tiny session-backed
  object you can swap out; see `tests/conftest.py`.

## Install

```bash
pip install espn-fantasy-baseball-api
```

Or from source:

```bash
git clone https://github.com/anthonysawah/espn-fantasy-baseball-api
cd espn-fantasy-baseball-api
pip install -e ".[dev]"
```

Requires Python 3.9+.

## Quick start

### Public leagues

```python
from espn_fantasy_baseball import League

lg = League(league_id=123456, year=2024)

for team in lg.standings():
    print(f"{team.standings_rank:>2}  {team.name:<25}  {team.record}")
```

### Private leagues

1. Log in to [fantasy.espn.com](https://fantasy.espn.com) in your browser.
2. Open **DevTools → Application → Cookies → espn.com** and copy the values
   for `espn_s2` and `SWID` (the SWID is the thing wrapped in `{}`).
3. Pass them to `League`:

```python
lg = League(
    league_id=123456,
    year=2024,
    espn_s2="AECz...long-string...",
    swid="{12345678-ABCD-...}",
)
```

You can also set them via environment variables (`ESPN_S2`, `SWID`) when
using the CLI.

### Common workflows

```python
# Power rankings
for rank, (team, score) in enumerate(lg.power_rankings(), 1):
    print(f"{rank}. {team.name:<25} score={score:.2f} ({team.record})")

# Boxscore for a given week
for box in lg.boxscores(matchup_period=12):
    print(f"Home {box.home_team_id} {box.home_score} — Away {box.away_team_id} {box.away_score}")
    for p in box.home_lineup:
        print(f"  {p.lineup_slot:<5} {p.player.name:<25} {p.points:>5.1f}")

# Top-50 free agent shortstops by current ownership
for p in lg.free_agents(size=50, position="SS"):
    print(f"{p.name:<25} {p.pro_team:<4} owned={p.percent_owned:5.1f}%")

# Draft recap
for pick in lg.draft():
    print(f"R{pick.round}.{pick.round_pick} (#{pick.overall_pick}) → team {pick.team_id}: {pick.player_name}")

# League scoring rules
s = lg.settings()
for item in s.scoring:
    print(f"{item.stat_name}: {item.points:+.2f}")
```

## CLI

Installing the package adds an `espn-fb` command:

```bash
# Standings
espn-fb standings --league 123456 --year 2024

# A team's roster
espn-fb roster --league 123456 --year 2024 --team 1

# Week's matchups
espn-fb matchups --league 123456 --year 2024 --week 12

# Top 20 free-agent shortstops
espn-fb fa --league 123456 --year 2024 --position SS --size 20

# Draft recap
espn-fb draft --league 123456 --year 2024

# Power rankings
espn-fb power --league 123456 --year 2024

# League settings
espn-fb settings --league 123456 --year 2024
```

Set `ESPN_S2` and `SWID` in your environment (or pass `--espn-s2 / --swid`)
for private leagues.

## API surface

| Resource         | How to get it                                  |
| ---------------- | ---------------------------------------------- |
| `LeagueSettings` | `lg.settings()`                                |
| `list[Team]`     | `lg.teams()`, `lg.standings()`                 |
| `Team`           | `lg.team(team_id)`                             |
| `list[Matchup]`  | `lg.schedule()`, `lg.matchups(week)`, `lg.scoreboard()` |
| `list[Boxscore]` | `lg.boxscores(week)`                           |
| `list[DraftPick]`| `lg.draft()`                                   |
| `list[Player]`   | `lg.free_agents(...)`                          |
| `Player \| None` | `lg.player_by_id(pid)`                         |
| `list[Activity]` | `lg.recent_activity(size=25)`                  |

Every resource exposes a `.raw` attribute with the original JSON, so you
never lose access to anything ESPN returns.

## Error handling

All exceptions subclass `ESPNFantasyError`:

- `PrivateLeagueError` – league is private and you didn't supply (valid) cookies.
- `LeagueNotFoundError` – 404 from ESPN (bad `league_id`).
- `InvalidSeasonError` – ESPN rejected the season id (future year, very old league).
- `ESPNAPIError` – anything else (non-2xx, non-JSON response, network error after retries).

```python
from espn_fantasy_baseball import League
from espn_fantasy_baseball.exceptions import PrivateLeagueError

try:
    lg = League(league_id=9999, year=2024).settings()
except PrivateLeagueError:
    print("Need cookies for that league.")
```

## Testing

```bash
pip install -e ".[dev]"
pytest
```

The test suite uses a small `FakeSession` in `tests/conftest.py` and
deterministic JSON fixtures; no network access required.

## Caveats

- ESPN's API is **not public**. Endpoints, field names and semantics can
  change without warning. This library pins to the behavior observed as of
  the 2024 season and ships with a test suite that documents that shape.
- The client is **read-only**. Lineup edits, add/drop and trade proposals
  go through a separate authenticated write host and are out of scope.
- This project is not affiliated with, endorsed by, or sponsored by ESPN
  or MLB.

## License

MIT — see [LICENSE](./LICENSE).
