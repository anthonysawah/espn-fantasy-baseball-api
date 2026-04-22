"""League settings — name, scoring, roster composition, etc."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from ..constants import LINEUP_SLOT_MAP, STAT_ID_MAP
from ..utils import coerce_float, coerce_int


@dataclass
class ScoringItem:
    """One line in the scoring settings: stat -> points per unit."""

    stat_id: int
    stat_name: str
    points: float
    is_reverse: bool = False

    @classmethod
    def from_raw(cls, raw: Mapping[str, Any]) -> ScoringItem:
        sid = coerce_int(raw.get("statId"))
        return cls(
            stat_id=sid,
            stat_name=STAT_ID_MAP.get(sid, f"STAT_{sid}"),
            points=coerce_float(raw.get("points")),
            is_reverse=bool(raw.get("isReverseItem", False)),
        )


@dataclass
class LeagueSettings:
    """A structured view over ``settings`` from ``mSettings``."""

    name: str
    season: int
    size: int
    scoring_type: str
    playoff_teams: int
    regular_season_matchup_periods: int
    trade_deadline: int | None
    roster_slots: dict[str, int] = field(default_factory=dict)
    scoring: list[ScoringItem] = field(default_factory=list)
    tie_rule: str | None = None
    acquisition_budget: int | None = None
    uses_waiver: bool = False
    raw: Mapping[str, Any] | None = field(default=None, repr=False)

    @classmethod
    def from_raw(cls, league_raw: Mapping[str, Any]) -> LeagueSettings:
        settings = league_raw.get("settings") or {}
        scoring = (settings.get("scoringSettings") or {})
        roster = (settings.get("rosterSettings") or {})
        schedule = (settings.get("scheduleSettings") or {})

        lineup_slot_counts = roster.get("lineupSlotCounts") or {}
        roster_slots = {
            LINEUP_SLOT_MAP.get(int(k), f"SLOT_{k}"): int(v)
            for k, v in lineup_slot_counts.items()
            if int(v) > 0
        }

        scoring_items = [
            ScoringItem.from_raw(item)
            for item in (scoring.get("scoringItems") or [])
        ]

        return cls(
            name=settings.get("name") or "",
            season=coerce_int(league_raw.get("seasonId")),
            size=coerce_int(settings.get("size")),
            scoring_type=_scoring_type(scoring.get("scoringType")),
            playoff_teams=coerce_int(schedule.get("playoffTeamCount")),
            regular_season_matchup_periods=coerce_int(schedule.get("matchupPeriodCount")),
            trade_deadline=settings.get("tradeSettings", {}).get("deadlineDate"),
            roster_slots=roster_slots,
            scoring=scoring_items,
            tie_rule=scoring.get("playoffMatchupTieRule"),
            acquisition_budget=settings.get("acquisitionSettings", {}).get("acquisitionBudget"),
            uses_waiver=bool(settings.get("acquisitionSettings", {}).get("waiverProcessDays")),
            raw=league_raw,
        )


def _scoring_type(code: Any) -> str:
    # ESPN uses string enums like "H2H_POINTS", "H2H_CATEGORY", "ROTO", "POINTS".
    if not code:
        return "UNKNOWN"
    return str(code)
