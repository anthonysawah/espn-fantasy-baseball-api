"""The :class:`Boxscore` resource — a matchup with per-player stats."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from ..constants import LINEUP_SLOT_MAP
from ..utils import coerce_float, coerce_int, decode_stats
from .player import Player


@dataclass
class BoxscorePlayer:
    """A single player's line inside a boxscore."""

    player: Player
    lineup_slot: str | None
    points: float
    stats: dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_raw(cls, entry: Mapping[str, Any]) -> "BoxscorePlayer":
        pool = entry.get("playerPoolEntry", {})
        info = pool.get("player", {})
        applied = 0.0
        stats: dict[str, float] = {}
        # The matchup-period split that we want is the one whose stats match
        # this lineup period.  ESPN stores it inline on playerPoolEntry.
        for s in info.get("stats", []):
            # source 0 = real, and the "period" split matches the current period
            if s.get("statSourceId") == 0 and s.get("statSplitTypeId") in (1, 5):
                applied = coerce_float(s.get("appliedTotal"))
                stats = decode_stats(s.get("stats"))
                break
        # Fallbacks: ESPN sometimes puts the applied total directly on the entry.
        if not applied:
            applied = coerce_float(pool.get("appliedStatTotal"))
        return cls(
            player=Player.from_roster_entry(entry),
            lineup_slot=LINEUP_SLOT_MAP.get(coerce_int(entry.get("lineupSlotId"))),
            points=applied,
            stats=stats,
        )


@dataclass
class Boxscore:
    """Full boxscore for a single matchup (both teams, both rosters)."""

    matchup_period: int
    matchup_id: int
    home_team_id: int | None
    away_team_id: int | None
    home_score: float
    away_score: float
    home_lineup: list[BoxscorePlayer] = field(default_factory=list)
    away_lineup: list[BoxscorePlayer] = field(default_factory=list)
    raw: Mapping[str, Any] | None = field(default=None, repr=False)

    @classmethod
    def from_raw(cls, raw: Mapping[str, Any]) -> "Boxscore":
        home = raw.get("home") or {}
        away = raw.get("away") or {}

        home_entries = ((home.get("rosterForCurrentScoringPeriod") or {}).get("entries")) or []
        away_entries = ((away.get("rosterForCurrentScoringPeriod") or {}).get("entries")) or []
        if not home_entries:
            home_entries = ((home.get("rosterForMatchupPeriod") or {}).get("entries")) or []
        if not away_entries:
            away_entries = ((away.get("rosterForMatchupPeriod") or {}).get("entries")) or []

        return cls(
            matchup_period=coerce_int(raw.get("matchupPeriodId")),
            matchup_id=coerce_int(raw.get("id")),
            home_team_id=home.get("teamId"),
            away_team_id=away.get("teamId"),
            home_score=coerce_float(home.get("totalPoints")),
            away_score=coerce_float(away.get("totalPoints")),
            home_lineup=[BoxscorePlayer.from_raw(e) for e in home_entries],
            away_lineup=[BoxscorePlayer.from_raw(e) for e in away_entries],
            raw=raw,
        )

    def winner(self) -> str | None:
        if self.home_score > self.away_score:
            return "HOME"
        if self.away_score > self.home_score:
            return "AWAY"
        if self.home_score and self.away_score:
            return "TIE"
        return None
