"""The :class:`Team` resource."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from ..utils import coerce_float, coerce_int
from .player import Player


@dataclass
class Team:
    """A fantasy team in an ESPN league."""

    id: int
    abbreviation: str
    name: str
    owner_ids: list[str] = field(default_factory=list)
    owner_names: list[str] = field(default_factory=list)
    logo_url: str | None = None
    division_id: int | None = None
    wins: int = 0
    losses: int = 0
    ties: int = 0
    points_for: float = 0.0
    points_against: float = 0.0
    playoff_seed: int | None = None
    standings_rank: int | None = None
    waiver_rank: int | None = None
    moves: int = 0
    trades: int = 0
    acquisition_budget_spent: int = 0
    roster: list[Player] = field(default_factory=list)
    raw: Mapping[str, Any] | None = field(default=None, repr=False)

    @classmethod
    def from_raw(
        cls,
        raw: Mapping[str, Any],
        *,
        members_by_id: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> "Team":
        members_by_id = members_by_id or {}
        owner_ids = list(raw.get("owners") or [])
        owner_names = [
            _format_member_name(members_by_id.get(o, {})) for o in owner_ids
        ]

        record = (raw.get("record") or {}).get("overall") or {}
        transaction_counter = raw.get("transactionCounter") or {}
        roster_entries = ((raw.get("roster") or {}).get("entries")) or []

        return cls(
            id=coerce_int(raw.get("id")),
            abbreviation=raw.get("abbrev") or "",
            name=_team_display_name(raw),
            owner_ids=owner_ids,
            owner_names=[n for n in owner_names if n],
            logo_url=raw.get("logo"),
            division_id=raw.get("divisionId"),
            wins=coerce_int(record.get("wins")),
            losses=coerce_int(record.get("losses")),
            ties=coerce_int(record.get("ties")),
            points_for=coerce_float(record.get("pointsFor")),
            points_against=coerce_float(record.get("pointsAgainst")),
            playoff_seed=raw.get("playoffSeed"),
            standings_rank=raw.get("rankCalculatedFinal") or raw.get("currentProjectedRank"),
            waiver_rank=raw.get("waiverRank"),
            moves=coerce_int(transaction_counter.get("moveToActive", 0))
            + coerce_int(transaction_counter.get("acquisitions", 0)),
            trades=coerce_int(transaction_counter.get("trades", 0)),
            acquisition_budget_spent=coerce_int(transaction_counter.get("acquisitionBudgetSpent", 0)),
            roster=[Player.from_roster_entry(e) for e in roster_entries],
            raw=raw,
        )

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    @property
    def record(self) -> str:
        return f"{self.wins}-{self.losses}" + (f"-{self.ties}" if self.ties else "")

    def starters(self) -> list[Player]:
        return [p for p in self.roster if p.lineup_slot not in {"BE", "Bench", "IL", None}]

    def bench(self) -> list[Player]:
        return [p for p in self.roster if p.lineup_slot in {"BE", "Bench"}]

    def injured(self) -> list[Player]:
        return [p for p in self.roster if p.lineup_slot == "IL"]

    def __repr__(self) -> str:  # pragma: no cover
        return f"Team({self.id}, {self.name!r}, {self.record})"


def _format_member_name(member: Mapping[str, Any]) -> str:
    if not member:
        return ""
    first = member.get("firstName") or ""
    last = member.get("lastName") or ""
    display = (first + " " + last).strip()
    return display or member.get("displayName") or ""


def _team_display_name(raw: Mapping[str, Any]) -> str:
    """Handle ESPN's several ways of representing a team name."""
    name = raw.get("name")
    if name:
        return name
    parts = [raw.get("location"), raw.get("nickname")]
    return " ".join(p for p in parts if p).strip() or raw.get("abbrev") or f"Team {raw.get('id')}"
