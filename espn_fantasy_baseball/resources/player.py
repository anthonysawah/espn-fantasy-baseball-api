"""The :class:`Player` resource."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from ..constants import INJURY_STATUS_MAP, LINEUP_SLOT_MAP
from ..utils import coerce_float, coerce_int, decode_positions, decode_pro_team, decode_stats


@dataclass
class PlayerStats:
    """A single row of a player's stats (season / projection / split)."""

    season: int
    source: str  # "real" | "projected"
    split: str   # "season" | "last_7" | "last_15" | "last_30" | "date_range"
    stats: dict[str, float] = field(default_factory=dict)
    applied_total: float = 0.0

    @classmethod
    def from_raw(cls, raw: Mapping[str, Any]) -> PlayerStats:
        source_id = raw.get("statSourceId")
        split_id = raw.get("statSplitTypeId")
        from ..constants import STAT_SOURCE, STAT_SPLIT

        return cls(
            season=coerce_int(raw.get("seasonId")),
            source=STAT_SOURCE.get(coerce_int(source_id), str(source_id)),
            split=STAT_SPLIT.get(coerce_int(split_id), str(split_id)),
            stats=decode_stats(raw.get("stats")),
            applied_total=coerce_float(raw.get("appliedTotal")),
        )


@dataclass
class Player:
    """A baseball player, as rostered / projected by ESPN."""

    id: int
    name: str
    pro_team: str
    eligible_positions: list[str] = field(default_factory=list)
    lineup_slot: str | None = None
    injury_status: str | None = None
    active_status: str | None = None
    acquisition_type: str | None = None  # DRAFT, FA, WAIVER, TRADE
    percent_owned: float = 0.0
    percent_started: float = 0.0
    stats: list[PlayerStats] = field(default_factory=list)
    raw: Mapping[str, Any] | None = field(default=None, repr=False)

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @classmethod
    def from_roster_entry(cls, entry: Mapping[str, Any]) -> Player:
        """Build a :class:`Player` from a ``roster.entries[i]`` dict."""
        player_pool = entry.get("playerPoolEntry", {})
        info = player_pool.get("player", {})
        injury = info.get("injuryStatus")
        ownership = info.get("ownership") or {}
        return cls(
            id=coerce_int(info.get("id")),
            name=info.get("fullName") or info.get("lastName") or "",
            pro_team=decode_pro_team(info.get("proTeamId")),
            eligible_positions=decode_positions(info.get("eligibleSlots")),
            lineup_slot=LINEUP_SLOT_MAP.get(coerce_int(entry.get("lineupSlotId")), None),
            injury_status=INJURY_STATUS_MAP.get(injury, injury) if injury else None,
            active_status=info.get("status"),
            acquisition_type=entry.get("acquisitionType"),
            percent_owned=coerce_float(ownership.get("percentOwned")),
            percent_started=coerce_float(ownership.get("percentStarted")),
            stats=[PlayerStats.from_raw(s) for s in info.get("stats", [])],
            raw=entry,
        )

    @classmethod
    def from_player_pool(cls, pool_entry: Mapping[str, Any]) -> Player:
        """Build a :class:`Player` from a free-agent / player-pool entry."""
        info = pool_entry.get("player", {})
        injury = info.get("injuryStatus")
        ownership = info.get("ownership") or {}
        return cls(
            id=coerce_int(info.get("id")),
            name=info.get("fullName") or info.get("lastName") or "",
            pro_team=decode_pro_team(info.get("proTeamId")),
            eligible_positions=decode_positions(info.get("eligibleSlots")),
            lineup_slot=None,
            injury_status=INJURY_STATUS_MAP.get(injury, injury) if injury else None,
            active_status=info.get("status"),
            acquisition_type=None,
            percent_owned=coerce_float(ownership.get("percentOwned")),
            percent_started=coerce_float(ownership.get("percentStarted")),
            stats=[PlayerStats.from_raw(s) for s in info.get("stats", [])],
            raw=pool_entry,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def season_stats(self, year: int | None = None, *, projected: bool = False) -> dict[str, float]:
        """Return the season-level stats dict for a given year."""
        source = "projected" if projected else "real"
        for s in self.stats:
            if s.split == "season" and s.source == source and (year is None or s.season == year):
                return dict(s.stats)
        return {}

    def is_pitcher(self) -> bool:
        return any(pos in {"P", "SP", "RP"} for pos in self.eligible_positions)

    def is_batter(self) -> bool:
        return not self.is_pitcher()

    def __repr__(self) -> str:  # pragma: no cover
        return f"Player({self.name!r}, {self.pro_team}, {'/'.join(self.eligible_positions) or '?'})"
