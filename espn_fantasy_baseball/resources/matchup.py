"""The :class:`Matchup` resource (schedule / scoreboard entry)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ..utils import coerce_float, coerce_int


@dataclass
class Matchup:
    """One matchup in the fantasy schedule."""

    matchup_period: int
    matchup_id: int
    playoff_tier: str | None
    winner: str | None  # "HOME", "AWAY", "TIE", or None (not played yet)
    home_team_id: int | None
    away_team_id: int | None
    home_score: float
    away_score: float
    home_projected: float | None
    away_projected: float | None
    raw: Mapping[str, Any]

    @classmethod
    def from_raw(cls, raw: Mapping[str, Any]) -> Matchup:
        home = raw.get("home") or {}
        away = raw.get("away") or {}
        return cls(
            matchup_period=coerce_int(raw.get("matchupPeriodId")),
            matchup_id=coerce_int(raw.get("id")),
            playoff_tier=raw.get("playoffTierType"),
            winner=raw.get("winner") if raw.get("winner") != "UNDECIDED" else None,
            home_team_id=home.get("teamId"),
            away_team_id=away.get("teamId"),
            home_score=coerce_float(home.get("totalPoints")),
            away_score=coerce_float(away.get("totalPoints")),
            home_projected=home.get("totalProjectedPointsLive"),
            away_projected=away.get("totalProjectedPointsLive"),
            raw=raw,
        )

    @property
    def is_bye(self) -> bool:
        return self.home_team_id is None or self.away_team_id is None

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"Matchup(period={self.matchup_period}, "
            f"{self.home_team_id}:{self.home_score} vs "
            f"{self.away_team_id}:{self.away_score})"
        )
