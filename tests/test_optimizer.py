"""Tests for the lineup optimizer."""

from __future__ import annotations

from dataclasses import replace

from espn_fantasy_baseball import LineupPlan, optimize_lineup
from espn_fantasy_baseball.resources import Player, PlayerStats


def _player(pid, name, positions, slot="BE", projected=0.0, injury=None):
    return Player(
        id=pid,
        name=name,
        pro_team="NYY",
        eligible_positions=list(positions),
        lineup_slot=slot,
        injury_status=injury,
        stats=[
            PlayerStats(season=2024, source="projected", split="season",
                        stats={}, applied_total=projected)
        ],
    )


def test_optimizer_assigns_highest_scorers_to_starter_slots(fake_league) -> None:
    # Alice's roster has a catcher (100, 310 pts), an SP (101, 445 pts), and
    # a benched OF (102).  With her league's roster slots the SP must start.
    alice = fake_league.team(1)
    plan = fake_league.optimize_lineup(alice)
    assert isinstance(plan, LineupPlan)
    # The top-scoring SP lands in an SP or P slot.
    ace_move = next(m for m in plan.moves if m.player.name == "Ace Anderson")
    assert ace_move.to_slot in {"SP", "P"}


def test_projections_override_default_scores(fake_league) -> None:
    alice = fake_league.team(1)
    # Lie to the optimizer: say Bench Bob is worth a trillion points, forcing
    # him into the OF slot over any other OF.
    plan = fake_league.optimize_lineup(alice, projections={102: 1_000_000})
    bob_move = next(m for m in plan.moves if m.player.name == "Benchy Bob")
    assert bob_move.to_slot in {"OF", "LF", "CF", "RF", "UTIL"}


def test_injured_player_goes_to_il_when_available(fake_league) -> None:
    # Force Benchy Bob's injury status to an IL variant.
    alice = fake_league.team(1)
    for i, p in enumerate(alice.roster):
        if p.name == "Benchy Bob":
            alice.roster[i] = replace(p, injury_status="10-Day IL")
    plan = fake_league.optimize_lineup(alice)
    bob_move = next(m for m in plan.moves if m.player.name == "Benchy Bob")
    assert bob_move.to_slot == "IL"


def test_unfilled_slots_are_reported() -> None:
    # Build a tiny synthetic scenario where we demand two SPs but have only one.
    from espn_fantasy_baseball.resources import LeagueSettings, Team

    roster = [
        _player(1, "Only SP", ["SP"], projected=100),
        _player(2, "Bench bat", ["1B"], projected=10),
    ]
    team = Team(id=1, abbreviation="ZZZ", name="Z", owner_ids=[], owner_names=[], roster=roster)
    settings = LeagueSettings(
        name="x", season=2024, size=1, scoring_type="H2H_POINTS",
        playoff_teams=0, regular_season_matchup_periods=0, trade_deadline=None,
        roster_slots={"SP": 2, "BE": 2},
    )
    plan = optimize_lineup(team, settings)
    assert "SP" in plan.unfilled_slots
    assert plan.projected_total == 100.0


def test_plan_summary_is_human_readable(fake_league) -> None:
    alice = fake_league.team(1)
    plan = fake_league.optimize_lineup(alice)
    text = plan.summary()
    assert "Projected total" in text
