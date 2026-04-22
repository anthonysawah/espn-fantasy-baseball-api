"""Derived / analytical helpers that work on top of the core resources.

These functions don't hit the network — they're pure transformations
over what :class:`~espn_fantasy_baseball.League` returns.  Keeping them
separate from the resource dataclasses stops the public dataclass API
from sprawling and makes them easy to unit-test.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from .resources import Boxscore, BoxscorePlayer, Matchup, Team

# ---------------------------------------------------------------------------
# Matchup summaries
# ---------------------------------------------------------------------------


@dataclass
class MatchupSummary:
    """Human-readable summary of a single matchup."""

    period: int
    home_team: Team
    away_team: Team
    home_score: float
    away_score: float
    margin: float                 # home minus away
    winner_team: Team | None
    loser_team: Team | None
    is_final: bool

    @property
    def headline(self) -> str:
        if self.winner_team is None or self.loser_team is None:
            return f"{self.away_team.name} {self.away_score:.1f} @ {self.home_team.name} {self.home_score:.1f} (in progress)"
        margin = abs(self.margin)
        return f"{self.winner_team.name} beat {self.loser_team.name} by {margin:.1f}"


def summarize_matchup(matchup: Matchup, teams_by_id: dict[int, Team]) -> MatchupSummary:
    """Decorate a raw :class:`Matchup` with team references + derived fields."""
    home_team = teams_by_id[matchup.home_team_id] if matchup.home_team_id else _PLACEHOLDER_TEAM
    away_team = teams_by_id[matchup.away_team_id] if matchup.away_team_id else _PLACEHOLDER_TEAM
    winner = None
    loser = None
    if matchup.winner == "HOME":
        winner, loser = home_team, away_team
    elif matchup.winner == "AWAY":
        winner, loser = away_team, home_team
    return MatchupSummary(
        period=matchup.matchup_period,
        home_team=home_team,
        away_team=away_team,
        home_score=matchup.home_score,
        away_score=matchup.away_score,
        margin=matchup.home_score - matchup.away_score,
        winner_team=winner,
        loser_team=loser,
        is_final=matchup.winner is not None,
    )


# Sentinel used when a matchup references a bye/unknown team id.
_PLACEHOLDER_TEAM = Team(
    id=-1, abbreviation="BYE", name="Bye", owner_ids=[], owner_names=[]
)


# ---------------------------------------------------------------------------
# Boxscore insights
# ---------------------------------------------------------------------------


@dataclass
class BoxscoreInsights:
    """Top performers / under-performers / bench points for a boxscore."""

    boxscore: Boxscore
    top_home: BoxscorePlayer | None
    top_away: BoxscorePlayer | None
    bench_points_home: float
    bench_points_away: float
    starters_home: list[BoxscorePlayer]
    starters_away: list[BoxscorePlayer]


def analyze_boxscore(boxscore: Boxscore) -> BoxscoreInsights:
    """Return :class:`BoxscoreInsights` for a single boxscore."""
    home_starters = [e for e in boxscore.home_lineup if e.lineup_slot not in {"BE", "Bench", "IL", None}]
    away_starters = [e for e in boxscore.away_lineup if e.lineup_slot not in {"BE", "Bench", "IL", None}]
    home_bench = [e for e in boxscore.home_lineup if e.lineup_slot in {"BE", "Bench"}]
    away_bench = [e for e in boxscore.away_lineup if e.lineup_slot in {"BE", "Bench"}]

    return BoxscoreInsights(
        boxscore=boxscore,
        top_home=max(home_starters, key=lambda e: e.points, default=None),
        top_away=max(away_starters, key=lambda e: e.points, default=None),
        bench_points_home=sum(e.points for e in home_bench),
        bench_points_away=sum(e.points for e in away_bench),
        starters_home=home_starters,
        starters_away=away_starters,
    )


# ---------------------------------------------------------------------------
# Whole-season tools
# ---------------------------------------------------------------------------


def strength_of_schedule(
    team: Team,
    schedule: Sequence[Matchup],
    teams_by_id: dict[int, Team],
) -> float:
    """Average points-for of every opponent a team has faced.

    Higher number = tougher schedule.  Returns 0.0 if the team hasn't
    played anyone yet.
    """
    opponents: list[Team] = []
    for m in schedule:
        if m.home_team_id == team.id and m.away_team_id in teams_by_id:
            opponents.append(teams_by_id[m.away_team_id])
        elif m.away_team_id == team.id and m.home_team_id in teams_by_id:
            opponents.append(teams_by_id[m.home_team_id])
    if not opponents:
        return 0.0
    return sum(t.points_for for t in opponents) / len(opponents)


def close_games(
    schedule: Iterable[Matchup],
    *,
    margin_threshold: float = 5.0,
) -> list[Matchup]:
    """Matchups decided by less than ``margin_threshold`` points (finals only)."""
    out: list[Matchup] = []
    for m in schedule:
        if m.winner is None:
            continue
        if abs(m.home_score - m.away_score) < margin_threshold:
            out.append(m)
    return out


def longest_win_streak(team: Team, schedule: Sequence[Matchup]) -> int:
    """Length of the team's longest winning streak in the given schedule."""
    current = best = 0
    relevant = sorted(
        (m for m in schedule if team.id in (m.home_team_id, m.away_team_id) and m.winner),
        key=lambda m: m.matchup_period,
    )
    for m in relevant:
        won = (m.winner == "HOME" and m.home_team_id == team.id) or (
            m.winner == "AWAY" and m.away_team_id == team.id
        )
        current = current + 1 if won else 0
        best = max(best, current)
    return best
