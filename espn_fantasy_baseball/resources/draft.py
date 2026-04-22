"""The :class:`DraftPick` resource."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ..utils import coerce_int


@dataclass
class DraftPick:
    """A single pick from a league's draft detail payload."""

    overall_pick: int
    round: int
    round_pick: int
    team_id: int
    player_id: int
    player_name: str | None
    bid_amount: int | None
    keeper: bool
    auto_drafted: bool
    nominating_team_id: int | None
    raw: Mapping[str, Any]

    @classmethod
    def from_raw(cls, raw: Mapping[str, Any], *, player_names: Mapping[int, str] | None = None) -> DraftPick:
        player_id = coerce_int(raw.get("playerId"))
        name = None
        if player_names:
            name = player_names.get(player_id)
        return cls(
            overall_pick=coerce_int(raw.get("overallPickNumber")),
            round=coerce_int(raw.get("roundId")),
            round_pick=coerce_int(raw.get("roundPickNumber")),
            team_id=coerce_int(raw.get("teamId")),
            player_id=player_id,
            player_name=name,
            bid_amount=coerce_int(raw.get("bidAmount")) if raw.get("bidAmount") is not None else None,
            keeper=bool(raw.get("keeper", False)),
            auto_drafted=bool(raw.get("autoDraftTypeId")),
            nominating_team_id=raw.get("nominatingTeamId"),
            raw=raw,
        )

    def __repr__(self) -> str:  # pragma: no cover
        label = self.player_name or f"Player#{self.player_id}"
        return f"Pick({self.overall_pick}: team={self.team_id} → {label})"
