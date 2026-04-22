"""League activity / transaction feed."""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Any, Mapping

from ..constants import ACTIVITY_MAP
from ..utils import coerce_int


@dataclass
class ActivityAction:
    """One atomic action inside an activity (add/drop/trade-leg/etc)."""

    type: str  # "FA", "WAIVER", "DROP", "TRADE", ...
    team_id: int | None
    player_id: int
    player_name: str | None = None
    bid_amount: int | None = None
    raw: Mapping[str, Any] | None = None

    @classmethod
    def from_raw(cls, raw: Mapping[str, Any]) -> "ActivityAction":
        type_id = coerce_int(raw.get("type") or raw.get("msgTypeId"))
        return cls(
            type=ACTIVITY_MAP.get(type_id, f"TYPE_{type_id}"),
            team_id=raw.get("toTeamId") if raw.get("toTeamId") != -1 else raw.get("fromTeamId"),
            player_id=coerce_int(raw.get("playerId")),
            bid_amount=raw.get("bidAmount"),
            raw=raw,
        )


@dataclass
class Activity:
    """A single activity event (e.g. a trade, a waiver claim, a lineup change)."""

    id: str
    date: _dt.datetime | None
    type: str
    actions: list[ActivityAction] = field(default_factory=list)
    raw: Mapping[str, Any] | None = field(default=None, repr=False)

    @classmethod
    def from_raw(cls, raw: Mapping[str, Any]) -> "Activity":
        date_ms = raw.get("date")
        date = (
            _dt.datetime.fromtimestamp(date_ms / 1000, tz=_dt.timezone.utc)
            if date_ms
            else None
        )
        actions_raw = raw.get("messages") or raw.get("items") or []
        actions = [ActivityAction.from_raw(a) for a in actions_raw]
        overall_type = _summarize(actions)
        return cls(
            id=str(raw.get("id") or raw.get("guid") or ""),
            date=date,
            type=overall_type,
            actions=actions,
            raw=raw,
        )

    def __repr__(self) -> str:  # pragma: no cover
        return f"Activity({self.type}, {self.date}, {len(self.actions)} action(s))"


def _summarize(actions: list[ActivityAction]) -> str:
    if not actions:
        return "UNKNOWN"
    types = {a.type for a in actions}
    if "TRADED" in types:
        return "TRADE"
    if "DROPPED" in types and any("ADDED" in t for t in types):
        return "ADD/DROP"
    return next(iter(types))
