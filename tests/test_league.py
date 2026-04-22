"""Tests for the high-level League facade."""

from __future__ import annotations


def test_settings_parses_top_level_fields(fake_league) -> None:
    s = fake_league.settings()
    assert s.name == "The Show"
    assert s.size == 10
    assert s.season == 2024
    assert s.scoring_type == "H2H_POINTS"
    assert s.playoff_teams == 4
    assert s.regular_season_matchup_periods == 22


def test_settings_roster_slots_are_human_readable(fake_league) -> None:
    s = fake_league.settings()
    assert s.roster_slots["C"] == 1
    assert s.roster_slots["OF"] == 3
    assert s.roster_slots["SP"] == 2
    assert s.roster_slots["RP"] == 2


def test_settings_scoring_items_decoded(fake_league) -> None:
    s = fake_league.settings()
    by_name = {item.stat_name: item for item in s.scoring}
    assert by_name["HR"].points == 4.0
    assert by_name["R"].points == 1.0
    assert by_name["SB"].points == 2.0
    assert by_name["W"].points == 5.0
    assert by_name["ERA"].is_reverse is True


def test_teams_are_decoded_with_records_and_owners(fake_league) -> None:
    teams = fake_league.teams()
    assert len(teams) == 3
    alice = next(t for t in teams if t.id == 1)
    assert alice.name == "Alice's Aces"
    assert alice.owner_names == ["Alice Anderson"]
    assert alice.record == "12-5-1"
    assert alice.points_for == 1422.5


def test_team_lookup_raises_keyerror(fake_league) -> None:
    import pytest

    with pytest.raises(KeyError):
        fake_league.team(999)


def test_roster_entries_are_players(fake_league) -> None:
    alice = fake_league.team(1)
    assert len(alice.roster) == 3
    catcher = next(p for p in alice.roster if p.name == "Catcher Clyde")
    assert catcher.pro_team == "NYY"
    assert "C" in catcher.eligible_positions
    assert catcher.lineup_slot == "C"


def test_roster_helpers(fake_league) -> None:
    alice = fake_league.team(1)
    assert {p.name for p in alice.starters()} == {"Catcher Clyde", "Ace Anderson"}
    assert {p.name for p in alice.bench()} == {"Benchy Bob"}


def test_player_season_stats_lookup(fake_league) -> None:
    alice = fake_league.team(1)
    ace = next(p for p in alice.roster if p.name == "Ace Anderson")
    stats = ace.season_stats(year=2024)
    assert stats["W"] == 18
    assert stats["K"] == 220


def test_standings_sorted_by_win_pct(fake_league) -> None:
    teams = fake_league.standings()
    assert [t.id for t in teams] == [1, 2, 3]


def test_schedule_and_matchups(fake_league) -> None:
    schedule = fake_league.schedule()
    assert len(schedule) == 3
    wk2 = fake_league.matchups(2)
    assert len(wk2) == 1
    assert wk2[0].winner is None  # UNDECIDED -> None
    wk1 = fake_league.matchups(1)
    assert {m.winner for m in wk1} == {"HOME", "AWAY"}


def test_scoreboard_defaults_to_current_period(fake_league) -> None:
    current = fake_league.scoreboard()
    assert len(current) == 1
    assert current[0].matchup_period == 2


def test_draft_is_parsed_and_named(fake_league) -> None:
    picks = fake_league.draft()
    assert len(picks) == 3
    first = picks[0]
    assert first.overall_pick == 1
    assert first.team_id == 1
    assert first.player_name == "Ace Anderson"
    assert first.bid_amount == 55


def test_free_agents_return_decoded_players(fake_league) -> None:
    fas = fake_league.free_agents(size=10)
    assert len(fas) == 2
    assert fas[0].name == "Free Agent One"
    assert fas[0].percent_owned == 48.2


def test_boxscore_includes_per_player_points(fake_league) -> None:
    boxes = fake_league.boxscores(2)
    assert len(boxes) == 1
    box = boxes[0]
    assert box.home_team_id == 1
    assert len(box.home_lineup) == 2
    ace = next(e for e in box.home_lineup if e.player.name == "Ace Anderson")
    assert ace.points == 33.8
    assert ace.stats["K"] == 8


def test_power_rankings_returns_all_teams_sorted(fake_league) -> None:
    ranked = fake_league.power_rankings()
    assert len(ranked) == 3
    # Scores must be monotonically non-increasing
    scores = [s for _, s in ranked]
    assert scores == sorted(scores, reverse=True)
    # Alice (best PF and best record) should be #1
    assert ranked[0][0].id == 1


def test_refresh_invalidates_cache(fake_league) -> None:
    fake_league.teams()
    assert fake_league._cache
    fake_league.refresh()
    assert fake_league._cache == {}
