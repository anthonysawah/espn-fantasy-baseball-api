# espn-fantasy-baseball-api

A modern, typed, friendly Python client for the **ESPN Fantasy Baseball** API.

[![CI](https://github.com/anthonysawah/espn-fantasy-baseball-api/actions/workflows/ci.yml/badge.svg)](https://github.com/anthonysawah/espn-fantasy-baseball-api/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/espn-fantasy-baseball-api.svg)](https://pypi.org/project/espn-fantasy-baseball-api/)
[![Python](https://img.shields.io/pypi/pyversions/espn-fantasy-baseball-api.svg)](https://pypi.org/project/espn-fantasy-baseball-api/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

> ESPN's Fantasy API is undocumented. This library reverse-engineers the
> public endpoints the espn.com UI uses, decodes ESPN's numeric slot /
> stat / position ids into human-readable names, and gives you real
> dataclasses for leagues, teams, players, matchups, boxscores, drafts,
> transactions, and settings.

---

## Table of contents

- [Features](#features)
- [Installation](#installation)
- [Quick start](#quick-start)
  - [Public leagues](#public-leagues)
  - [Private leagues](#private-leagues)
- [The CLI](#the-cli)
- [Recipes](#recipes)
- [API surface](#api-surface)
- [Error handling](#error-handling)
- [Testing](#testing)
- [Project layout](#project-layout)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [Caveats](#caveats)
- [License](#license)

---

## Features

- **Read the whole league** — settings, standings, schedules, matchups,
  boxscores, rosters, drafts, free agents, activity feed.
- **Manage the whole league** — set lineups, add / drop free agents and
  waiver claims (FAAB-aware), move players on and off the IL, propose
  and respond to trades.
- **Optimize your lineup** — a slot-aware solver that maximises projected
  points, routes injured players to the IL, and can submit the moves for
  you with one call.
- **Matchup analytics** — summaries, boxscore insights (top performer,
  bench points left on the table), strength-of-schedule, close-games,
  longest winning streak.
- **Private-league auth** via `espn_s2` / `SWID` cookies, with braces
  auto-normalized.
- **Decoded everything** — no more `stats["5"]`, you get `stats["HR"]`.
  Slot ids → position abbrevs. proTeamId → team abbrevs.
- **Typed dataclasses** for every resource, plus `.raw` access to the
  original payload so you never lose data.
- **Lazy + cached** — calls fire only when you ask, and repeated reads
  in the same `League` are served from an in-process cache.
  `lg.refresh()` to invalidate.
- **Retries on transient errors** (429 / 5xx) with exponential backoff.
- **Zero heavy deps** — just `requests`.
- **CLI** — `espn-fb optimize --team 1 --apply` and friends.
- **Test-friendly** — swap the `requests.Session` for your own mock;
  see `tests/conftest.py`.

---

## Installation

```bash
pip install espn-fantasy-baseball-api
```

From source:

```bash
git clone https://github.com/anthonysawah/espn-fantasy-baseball-api
cd espn-fantasy-baseball-api
pip install -e ".[dev]"
```

Requires **Python 3.9+**.

---

## Quick start

### Public leagues

```python
from espn_fantasy_baseball import League

lg = League(league_id=123456, year=2024)

for rank, team in enumerate(lg.standings(), 1):
    print(f"{rank:>2}. {team.name:<25}  {team.record}  PF={team.points_for:.1f}")
```

### Private leagues

1. Log in to [fantasy.espn.com](https://fantasy.espn.com) in your browser.
2. Open DevTools → Application → Cookies → `https://fantasy.espn.com`.
3. Copy the values of `espn_s2` and `SWID`.

```python
lg = League(
    league_id=123456,
    year=2024,
    espn_s2="AECz...long-token...",
    swid="{12345678-ABCD-...}",   # braces optional — we add them
)
```

You can also export `ESPN_S2` and `SWID` as environment variables — the
CLI and the example scripts pick them up automatically. See
[`docs/AUTHENTICATION.md`](./docs/AUTHENTICATION.md) for details and
security notes.

---

## The CLI

Installing the package adds an `espn-fb` command. All subcommands take
`--league` and `--year`; private leagues also take `--espn-s2` / `--swid`
(or read them from the environment).

**Read**

| Command | Purpose |
| --- | --- |
| `espn-fb standings` | Current standings, best record first. |
| `espn-fb roster --team ID` | Full roster for one team, by lineup slot. |
| `espn-fb matchups --week N` | Scoreboard for a given matchup period. |
| `espn-fb fa --position SS --size 20` | Top N free agents, optionally filtered. |
| `espn-fb draft` | The draft recap in overall-pick order. |
| `espn-fb power` | Blended power rankings (points-for + win-pct). |
| `espn-fb settings` | Name, size, scoring type, roster slots, scoring rules. |
| `espn-fb insights --week N` | Top performers + bench points per matchup. |

**Manage** (require `ESPN_S2` / `SWID`)

| Command | Purpose |
| --- | --- |
| `espn-fb optimize --team ID [--apply --period N]` | Show the optimal lineup; with `--apply`, submit it. |
| `espn-fb add --team ID --player PID [--drop PID --bid N --waiver]` | Free-agent or waiver pickup. |
| `espn-fb drop --team ID --player PID --period N` | Drop a player. |
| `espn-fb il-on --team ID --player PID --from-slot BE --period N` | Move onto IL. |
| `espn-fb il-off --team ID --player PID --to-slot BE --period N` | Activate off IL. |
| `espn-fb trade --team ID --to-team ID --offering … --requesting …` | Propose a trade. |

```bash
espn-fb standings --league 123456 --year 2024
espn-fb fa        --league 123456 --year 2024 --position SP --size 15
espn-fb roster    --league 123456 --year 2024 --team 1
```

---

## Recipes

### Power rankings

```python
for i, (team, score) in enumerate(lg.power_rankings(), 1):
    print(f"{i}. {team.name:<25}  score={score:7.2f}  ({team.record})")
```

### This week's scoreboard

```python
for m in lg.scoreboard():            # defaults to the current matchup period
    home = lg.team(m.home_team_id).name
    away = lg.team(m.away_team_id).name
    print(f"{away} {m.away_score:.1f} @ {m.home_score:.1f} {home}")
```

### Boxscore with per-player points

```python
for box in lg.boxscores(matchup_period=12):
    print(f"{box.home_team_id} {box.home_score} — {box.away_score} {box.away_team_id}")
    for p in box.home_lineup:
        print(f"  {p.lineup_slot:<5} {p.player.name:<25} {p.points:>5.1f}")
```

### Top free agents at a position

```python
for p in lg.free_agents(size=25, position="SP", sort_by="last7_points"):
    print(f"{p.name:<25} {p.pro_team:<4} owned={p.percent_owned:5.1f}%")
```

### Season stats for a specific player

```python
carlos = lg.player_by_id(33192)           # Carlos Correa, for example
print(carlos.season_stats(year=2024))     # -> {'H': 126, 'HR': 14, 'AVG': 0.285, ...}
```

### League scoring rules

```python
for item in lg.settings().scoring:
    print(f"{item.stat_name:>5}  {item.points:+5.2f}" + (" (reverse)" if item.is_reverse else ""))
```

### Recent transactions

```python
for event in lg.recent_activity(size=10):
    print(event.date, event.type)
    for a in event.actions:
        print(f"  team={a.team_id} {a.type:<12} player#{a.player_id}")
```

### Optimize and submit your lineup

```python
# Compute the best lineup by projected points
plan = lg.optimize_lineup(team_id=1)
print(plan.summary())

# Ship it — requires auth cookies
writer = lg.writer(team_id=1)
writer.apply_plan(plan, scoring_period=115)
```

### Add a free agent, drop a player, move to IL

```python
w = lg.writer(team_id=1)

w.add_player(player_id=41234, drop_player_id=39928, bid_amount=7, scoring_period=115)
w.move_to_il(player_id=39928, from_slot="2B", scoring_period=115)
w.drop_player(player_id=10001, scoring_period=115)
```

### Propose (or respond to) a trade

```python
w = lg.writer(team_id=1)
w.propose_trade(
    to_team_id=2,
    offering=[41234, 39928],
    requesting=[88888],
    expiration_days=2,
)
# Later, when a counterparty sends you one:
w.respond_to_trade(trade_id=77, accept=True)
```

### Matchup analytics

```python
for summary in lg.summarize_week(12):
    print(summary.headline)

for ins in lg.boxscore_insights(12):
    print(f"Top performer: {ins.top_home.player.name} ({ins.top_home.points:.1f})")
    print(f"Bench points left on the table: {ins.bench_points_home:.1f}")

# Strength of schedule, close games, streaks
print("Tough schedule?", lg.strength_of_schedule(team_id=1))
for m in lg.close_games(margin_threshold=5.0):
    print(m)
print("Longest win streak:", lg.longest_win_streak(team_id=1))
```

More recipes in [`docs/COOKBOOK.md`](./docs/COOKBOOK.md) and a complete
management guide in [`docs/MANAGING.md`](./docs/MANAGING.md).

---

## API surface

**Reading**

| Resource | How to get it |
| --- | --- |
| `LeagueSettings` | `lg.settings()` |
| `list[Team]` | `lg.teams()`, `lg.standings()` |
| `Team` | `lg.team(team_id)` |
| `list[Matchup]` | `lg.schedule()`, `lg.matchups(week)`, `lg.scoreboard()` |
| `list[Boxscore]` | `lg.boxscores(week)` |
| `list[DraftPick]` | `lg.draft()` |
| `list[Player]` | `lg.free_agents(size=..., position=..., sort_by=...)` |
| `Player \| None` | `lg.player_by_id(player_id)` |
| `list[Activity]` | `lg.recent_activity(size=25)` |
| `list[tuple[Team, float]]` | `lg.power_rankings(weights=...)` |

**Optimizing + analytics**

| Helper | How to get it |
| --- | --- |
| `LineupPlan` | `lg.optimize_lineup(team, projections=...)` |
| `list[MatchupSummary]` | `lg.summarize_week(week)` |
| `list[BoxscoreInsights]` | `lg.boxscore_insights(week)` |
| `float` (SoS) | `lg.strength_of_schedule(team)` |
| `list[Matchup]` | `lg.close_games(margin_threshold=5.0)` |
| `int` | `lg.longest_win_streak(team)` |

**Writing** (requires auth cookies)

| Operation | How to call it |
| --- | --- |
| `LeagueWriter` scoped to a team | `lg.writer(team_id)` |
| Apply optimizer result | `w.apply_plan(plan, scoring_period=...)` |
| Set lineup manually | `w.set_lineup(moves, scoring_period=...)` |
| Free-agent / waiver add | `w.add_player(pid, drop_player_id=..., bid_amount=..., scoring_period=..., via_waiver=False)` |
| Drop | `w.drop_player(pid, scoring_period=...)` |
| IL on / off | `w.move_to_il(pid, from_slot=..., scoring_period=...)` / `w.move_off_il(...)` |
| Propose trade | `w.propose_trade(to_team_id=..., offering=[...], requesting=[...])` |
| Accept / reject trade | `w.respond_to_trade(trade_id, accept=True)` |

Every resource also exposes `.raw` for the original ESPN JSON payload.
Full reference in [`docs/API.md`](./docs/API.md).

---

## Error handling

All exceptions subclass `ESPNFantasyError`:

| Exception | When |
| --- | --- |
| `PrivateLeagueError` | 401/403 — league is private and cookies are missing / expired. |
| `LeagueNotFoundError` | 404 — bad `league_id` for the season. |
| `InvalidSeasonError` | 400 — future season, or too far in the past. |
| `ESPNAPIError` | Any other non-2xx, non-JSON response, or exhausted retries. |

```python
from espn_fantasy_baseball import League
from espn_fantasy_baseball.exceptions import PrivateLeagueError

try:
    lg = League(league_id=9999, year=2024)
    lg.settings()
except PrivateLeagueError:
    print("Need cookies for that league.")
```

---

## Testing

```bash
pip install -e ".[dev]"
pytest
```

The suite ships with ~40 tests using a small `FakeSession` in
`tests/conftest.py` and deterministic JSON fixtures. No network access is
required. To run your own integration tests against a real league, set
`ESPN_S2` / `SWID` / `LEAGUE_ID` / `SEASON` in your environment and run
the scripts under `examples/`.

---

## Project layout

```
espn_fantasy_baseball/
├── __init__.py            public exports
├── client.py              ESPNClient: HTTP, auth, retries
├── constants.py           slot / stat / proTeam / view id maps
├── exceptions.py          error hierarchy
├── league.py              League facade (main entry point)
├── utils.py               stat/position/team decoders
├── cli.py                 the `espn-fb` command
└── resources/             dataclasses for each ESPN entity
    ├── team.py
    ├── player.py
    ├── matchup.py
    ├── boxscore.py
    ├── draft.py
    ├── activity.py
    └── settings.py

tests/                     unit tests + JSON fixtures
examples/                  runnable scripts (basic_usage, power_rankings, fa_finder)
docs/                      AUTHENTICATION, API, COOKBOOK, FAQ, CONTRIBUTING
```

---

## Documentation

- [`docs/AUTHENTICATION.md`](./docs/AUTHENTICATION.md) — how to find
  `espn_s2` / `SWID` and use them safely.
- [`docs/API.md`](./docs/API.md) — complete reference for every public
  class and method.
- [`docs/MANAGING.md`](./docs/MANAGING.md) — guide to lineup
  optimization, add/drop, IL moves, trades, and the CLI commands that
  drive them.
- [`docs/COOKBOOK.md`](./docs/COOKBOOK.md) — 20+ practical recipes.
- [`docs/FAQ.md`](./docs/FAQ.md) — common questions and troubleshooting.
- [`docs/CONTRIBUTING.md`](./docs/CONTRIBUTING.md) — dev setup, style,
  how to add a new endpoint.
- [`CHANGELOG.md`](./CHANGELOG.md) — version history.

---

## Contributing

PRs welcome! Please read
[`docs/CONTRIBUTING.md`](./docs/CONTRIBUTING.md) first. The tl;dr:

```bash
pip install -e ".[dev]"
ruff check .
mypy espn_fantasy_baseball
pytest
```

For bugs or feature requests, please open an
[issue](https://github.com/anthonysawah/espn-fantasy-baseball-api/issues)
— there are templates to help.

Security reports: see [`SECURITY.md`](./SECURITY.md).

---

## Caveats

- ESPN's API is **not public**. Endpoints, field names and semantics can
  change without warning. This library tracks behavior observed as of
  the 2024 season and ships with a test suite that documents it.
- Write operations hit `lm-api-writes.fantasy.espn.com`. ESPN sometimes
  returns `200 OK` with an error inside the payload for borderline
  illegal moves (e.g. a lineup change after lineup lock); the
  `WriteResult` exposes both the HTTP status and the response body so
  you can handle both.
- This project is not affiliated with, endorsed by, or sponsored by
  ESPN, MLB, or any Major League Baseball team. All product and company
  names are trademarks of their respective holders.

---

## License

[MIT](./LICENSE) — do anything you want, just don't sue us.
