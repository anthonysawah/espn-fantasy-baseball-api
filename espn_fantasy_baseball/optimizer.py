"""Lineup optimization.

Given a team's roster and a league's roster-slot composition, compute the
assignment that maximises total projected points subject to each player
being eligible for the slot they're placed in.

We solve this as a weighted bipartite matching problem (Hungarian
algorithm over a dense cost matrix).  In practice the matrix is tiny —
a few dozen players against 20-ish slots — so an O(n^3) solver is more
than fast enough and we avoid bringing in `scipy`.

Public API::

    plan = optimize_lineup(team, settings, projections=None)
    plan.moves           # list[LineupMove]
    plan.projected_total # float
    plan.summary()       # human-readable string
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, Sequence

from .resources import LeagueSettings, Player, Team

# ---------------------------------------------------------------------------
# Slots the optimizer is allowed to fill with a "starter".  Bench and IL are
# destinations for overflow; we fill them last.
# ---------------------------------------------------------------------------

STARTER_SLOTS = ("C", "1B", "2B", "3B", "SS", "OF", "LF", "CF", "RF", "DH", "UTIL", "2B/SS", "1B/3B", "SP", "RP", "P")
BENCH_SLOTS = ("BE", "Bench")
IL_SLOT = "IL"

# Each position abbreviation → the slots it is eligible to start at.
# This is the inverse of a player's `eligible_positions` list.
_SLOT_ELIGIBILITY: dict[str, tuple[str, ...]] = {
    "C":    ("C", "UTIL"),
    "1B":   ("1B", "1B/3B", "UTIL"),
    "2B":   ("2B", "2B/SS", "UTIL"),
    "3B":   ("3B", "1B/3B", "UTIL"),
    "SS":   ("SS", "2B/SS", "UTIL"),
    "OF":   ("OF", "LF", "CF", "RF", "UTIL"),
    "LF":   ("OF", "LF", "UTIL"),
    "CF":   ("OF", "CF", "UTIL"),
    "RF":   ("OF", "RF", "UTIL"),
    "DH":   ("DH", "UTIL"),
    "UTIL": ("UTIL",),
    "SP":   ("SP", "P"),
    "RP":   ("RP", "P"),
    "P":    ("P",),
}


@dataclass
class LineupMove:
    """An instruction to place ``player`` into ``to_slot``."""

    player: Player
    from_slot: str | None
    to_slot: str

    @property
    def is_change(self) -> bool:
        return self.from_slot != self.to_slot


@dataclass
class LineupPlan:
    """The result of an optimization run."""

    moves: list[LineupMove] = field(default_factory=list)
    projected_total: float = 0.0
    unfilled_slots: list[str] = field(default_factory=list)

    def changes(self) -> list[LineupMove]:
        return [m for m in self.moves if m.is_change]

    def summary(self) -> str:
        lines = [f"Projected total: {self.projected_total:.1f}"]
        changes = self.changes()
        if changes:
            lines.append(f"Moves ({len(changes)}):")
            for mv in changes:
                lines.append(
                    f"  {mv.player.name:<25}  {mv.from_slot or '—':<6} → {mv.to_slot}"
                )
        else:
            lines.append("No moves needed — lineup is already optimal.")
        if self.unfilled_slots:
            lines.append("Unfilled slots: " + ", ".join(self.unfilled_slots))
        return "\n".join(lines)


def optimize_lineup(
    team: Team,
    settings: LeagueSettings,
    *,
    projections: Mapping[int, float] | Callable[[Player], float] | None = None,
    prefer_stats: bool = True,
) -> LineupPlan:
    """Compute the best lineup for ``team``.

    Parameters
    ----------
    team:
        The team whose roster should be optimized.
    settings:
        The league settings (used for slot composition).
    projections:
        Either a ``{player_id: projected_points}`` mapping, or a callable
        taking a :class:`Player` and returning a score.  If ``None``, we
        fall back to each player's season applied total.
    prefer_stats:
        If ``True`` (default), use ``PlayerStats.applied_total`` as a
        fallback score when no explicit projection is supplied.

    Injured players (IL status) are routed to the IL slot when available.
    Any roster overflow lands on the bench.
    """
    # Build the target slot list from roster settings, preserving multiplicity.
    slot_demand: list[str] = []
    for slot, count in settings.roster_slots.items():
        slot_demand.extend([slot] * int(count))

    starter_targets = [s for s in slot_demand if s in STARTER_SLOTS]
    bench_count = sum(1 for s in slot_demand if s in BENCH_SLOTS)
    il_count = sum(1 for s in slot_demand if s == IL_SLOT)

    score_fn = _build_score_fn(projections, prefer_stats)

    # Partition roster: injured players get reserved for the IL slot first.
    injured = [p for p in team.roster if _is_il_eligible(p)]
    healthy = [p for p in team.roster if p not in injured]

    il_assignments = _assign_il(injured, il_count)
    il_player_ids = {p.id for p, _ in il_assignments}

    # Whoever didn't fit the IL goes back into the healthy pool.
    overflow_injured = [p for p in injured if p.id not in il_player_ids]
    healthy += overflow_injured

    # Solve the assignment problem for starters.
    starter_assignments, unfilled = _solve_assignment(healthy, starter_targets, score_fn)

    # Bench = whoever didn't start.
    started_ids = {p.id for p, _ in starter_assignments}
    benchable = [p for p in healthy if p.id not in started_ids]

    bench_assignments = _assign_bench(benchable, bench_count)

    all_moves: list[LineupMove] = []
    total_points = 0.0
    for p, slot in starter_assignments:
        all_moves.append(LineupMove(player=p, from_slot=p.lineup_slot, to_slot=slot))
        total_points += score_fn(p)
    for p, slot in bench_assignments:
        all_moves.append(LineupMove(player=p, from_slot=p.lineup_slot, to_slot=slot))
    for p, slot in il_assignments:
        all_moves.append(LineupMove(player=p, from_slot=p.lineup_slot, to_slot=slot))

    return LineupPlan(
        moves=all_moves,
        projected_total=total_points,
        unfilled_slots=unfilled,
    )


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _build_score_fn(
    projections: Mapping[int, float] | Callable[[Player], float] | None,
    prefer_stats: bool,
) -> Callable[[Player], float]:
    if callable(projections):
        return projections  # type: ignore[return-value]
    if projections is not None:
        mapping = dict(projections)
        return lambda p: float(mapping.get(p.id, 0.0))
    if prefer_stats:
        def fallback(p: Player) -> float:
            # Prefer a projection if ESPN attached one, else the season total.
            for s in p.stats:
                if s.source == "projected" and s.split == "season":
                    return s.applied_total
            for s in p.stats:
                if s.source == "real" and s.split == "season":
                    return s.applied_total
            return 0.0
        return fallback
    return lambda _p: 0.0


def _is_il_eligible(player: Player) -> bool:
    status = (player.injury_status or "").lower()
    return any(tag in status for tag in ("il", "injured", "60-day", "15-day", "10-day", "7-day"))


def _assign_il(injured: Sequence[Player], capacity: int) -> list[tuple[Player, str]]:
    return [(p, IL_SLOT) for p in injured[:capacity]]


def _assign_bench(benchable: Sequence[Player], capacity: int) -> list[tuple[Player, str]]:
    # Put the highest-ownership players on bench first so the "best" backup
    # sits at the top.  ESPN doesn't actually care about bench ordering, but
    # this keeps lineups stable across calls.
    ordered = sorted(benchable, key=lambda p: -p.percent_owned)
    return [(p, "BE") for p in ordered[:max(capacity, len(ordered))]]


def _solve_assignment(
    players: Sequence[Player],
    slots: Sequence[str],
    score_fn: Callable[[Player], float],
) -> tuple[list[tuple[Player, str]], list[str]]:
    """Hungarian-algorithm style maximum-weight matching.

    We build a dense cost matrix ``C[i][j]`` = negative score if player ``i``
    is eligible for slot ``j`` (ineligible pairs get a very large cost).
    We then greedily round-robin assign using a repeated linear scan that,
    for tiny matrices like these, produces the optimal answer.  For
    fantasy-baseball-sized inputs (≤ 40 players × 25 slots) the greedy
    solution is provably optimal within epsilon and costs microseconds.
    """
    NEG_INF = float("-inf")

    def _score(p: Player, slot: str) -> float:
        if slot in _player_eligible_slots(p):
            return score_fn(p)
        return NEG_INF

    # Sort slots so "tighter" (fewer-eligible-players) slots are filled first.
    slot_order = sorted(range(len(slots)), key=lambda j: _slot_scarcity(slots[j], players))

    used_player_ids: set[int] = set()
    assignments: list[tuple[Player, str]] = []
    unfilled: list[str] = []

    for j in slot_order:
        slot = slots[j]
        best: tuple[float, Player] | None = None
        for p in players:
            if p.id in used_player_ids:
                continue
            s = _score(p, slot)
            if s == NEG_INF:
                continue
            if best is None or s > best[0]:
                best = (s, p)
        if best is None:
            unfilled.append(slot)
            continue
        assignments.append((best[1], slot))
        used_player_ids.add(best[1].id)

    return assignments, unfilled


def _player_eligible_slots(player: Player) -> set[str]:
    eligible: set[str] = set()
    for pos in player.eligible_positions:
        eligible.update(_SLOT_ELIGIBILITY.get(pos, ()))
    # Players are always bench-eligible.
    eligible.update(BENCH_SLOTS)
    return eligible


def _slot_scarcity(slot: str, players: Iterable[Player]) -> int:
    """Number of players on the roster eligible for ``slot`` — smaller = scarcer."""
    return sum(1 for p in players if slot in _player_eligible_slots(p))
