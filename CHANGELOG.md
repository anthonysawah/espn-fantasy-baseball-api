# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
