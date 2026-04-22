# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.0] — 2026-04-22

### Added

- **Lineup optimizer** (`optimize_lineup` / `LineupPlan`) — a
  slot-aware, eligibility-respecting solver that maximises projected
  points and routes injured players to the IL.
- **Write API** (`LeagueWriter`) — `set_lineup`, `apply_plan`,
  `add_player` (free-agent + FAAB-aware waiver), `drop_player`,
  `move_to_il`, `move_off_il`, `propose_trade`, `respond_to_trade`.
- **Matchup analytics** — `summarize_week`, `boxscore_insights`,
  `strength_of_schedule`, `close_games`, `longest_win_streak`, plus
  standalone `MatchupSummary` and `BoxscoreInsights` dataclasses.
- CLI subcommands: `optimize`, `add`, `drop`, `il-on`, `il-off`,
  `trade`, `insights`.
- New guide: `docs/MANAGING.md` covering everything above.
- 22 new tests (optimizer, writer, analytics).

### Changed

- Package exports now include the optimizer, writer and analytics
  symbols.
- README reorganised into Read / Manage sections.

## [0.1.0] — 2026-04-22

### Added

- Initial release.
- `League` facade with methods for `settings`, `teams`, `team`,
  `standings`, `schedule`, `matchups`, `scoreboard`, `boxscores`,
  `draft`, `free_agents`, `player_by_id`, `recent_activity`,
  `power_rankings`.
- Resource dataclasses: `Team`, `Player`, `PlayerStats`, `Matchup`,
  `Boxscore`, `BoxscorePlayer`, `DraftPick`, `Activity`, `ActivityAction`,
  `LeagueSettings`, `ScoringItem`.
- `ESPNClient` HTTP layer with auth-cookie handling, exponential-backoff
  retries on 429/5xx, and granular exception types.
- `espn-fb` CLI covering the most common read operations.
- Full test suite using mocked HTTP responses; no network required.
- MIT license.
