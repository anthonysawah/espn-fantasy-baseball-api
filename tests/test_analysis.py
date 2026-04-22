"""Tests for the analytics helpers."""

from __future__ import annotations


def test_summarize_week_returns_one_entry_per_matchup(fake_league) -> None:
    summaries = fake_league.summarize_week(1)
    assert len(summaries) == 2
    s0 = summaries[0]
    assert s0.period == 1
    assert s0.is_final is True
    assert s0.winner_team is not None
    assert s0.loser_team is not None
    assert s0.headline.startswith(s0.winner_team.name)


def test_summarize_week_in_progress(fake_league) -> None:
    summaries = fake_league.summarize_week(2)
    assert summaries[0].is_final is False
    assert summaries[0].winner_team is None
    assert "in progress" in summaries[0].headline


def test_boxscore_insights_picks_top_starter(fake_league) -> None:
    ins = fake_league.boxscore_insights(2)
    assert len(ins) == 1
    box = ins[0]
    assert box.top_home is not None
    assert box.top_home.player.name == "Ace Anderson"
    assert box.top_home.points == 33.8


def test_close_games_filter(fake_league) -> None:
    tight = fake_league.close_games(margin_threshold=20.0)
    # Matchup 2 (30-pt margin) excluded; matchup 1 (15-pt) included; UNDECIDED excluded.
    assert len(tight) == 1
    assert tight[0].winner == "HOME"


def test_strength_of_schedule(fake_league) -> None:
    # Alice (team 1) played team 2 and team 3 in week 1.  SoS = mean PF of those teams.
    sos = fake_league.strength_of_schedule(1)
    teams_by_id = {t.id: t for t in fake_league.teams()}
    expected = (teams_by_id[2].points_for + teams_by_id[3].points_for) / 2
    # Team 1 is also in the week 2 match vs team 3 — counted again.
    # Team 1 appears in matches: wk1 vs team2, wk1 vs team3, wk2 vs team3.
    total = teams_by_id[2].points_for + teams_by_id[3].points_for + teams_by_id[3].points_for
    expected = total / 3
    assert abs(sos - expected) < 1e-6


def test_longest_win_streak(fake_league) -> None:
    # Alice (team 1) wins both week-1 matches in the fixture.
    streak = fake_league.longest_win_streak(1)
    assert streak == 2
