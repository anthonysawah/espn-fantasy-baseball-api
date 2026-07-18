# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.3.0] — 2026-07-18

### Added

- **AI advisor** (`Advisor` / `AdviceReport`) — builds a snapshot of your
  league (settings, standings, your roster with last-7/last-15 splits and
  injury statuses, current matchup, top free agents overall and by
  position, recent transactions) and asks Claude for prioritized
  pickup / drop / lineup / matchup recommendations.
- CLI subcommand: `espn-fb advise --team ID [--focus "..."] [--output F]`.
- Optional dependency extra: `pip install "espn-fantasy-baseball-api[ai]"`
  (installs the `anthropic` SDK).
- Scheduled GitHub Actions workflow (`.github/workflows/ai-advisor.yml`)
  that posts the daily report as a GitHub issue; configured entirely via
  repository secrets and skips quietly when unconfigured.
- New guide: `docs/AI_ADVISOR.md`.
- 8 new tests covering context building and the AI call (fully mocked).

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
