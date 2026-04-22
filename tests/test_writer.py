"""Tests for the write API."""

from __future__ import annotations

import pytest

from espn_fantasy_baseball import League
from espn_fantasy_baseball.exceptions import AuthenticationError


def test_writer_requires_cookies(fake_league: League) -> None:
    with pytest.raises(AuthenticationError):
        fake_league.writer(1)


def test_set_lineup_builds_expected_body(authed_league, fake_session) -> None:
    w = authed_league.writer(1)
    w.set_lineup(
        [
            {"player_id": 100, "from_slot": "BE", "to_slot": "C"},
            {"player_id": 101, "from_slot": 16, "to_slot": "SP"},
        ],
        scoring_period=115,
    )
    assert len(fake_session.posts) == 1
    url, body = fake_session.posts[0]
    assert "/transactions/" in url
    assert body["teamId"] == 1
    assert body["type"] == "LINEUP"
    assert body["scoringPeriodId"] == 115
    assert body["items"][0] == {
        "playerId": 100, "type": "LINEUP", "fromLineupSlotId": 16, "toLineupSlotId": 0,
    }
    assert body["items"][1]["toLineupSlotId"] == 14  # SP


def test_add_player_with_drop_and_bid(authed_league, fake_session) -> None:
    w = authed_league.writer(1)
    w.add_player(500, drop_player_id=102, bid_amount=17, scoring_period=115)
    _, body = fake_session.posts[-1]
    assert body["type"] == "FREEAGENT"
    assert body["bidAmount"] == 17
    assert body["executionType"] == "EXECUTE"
    types = {i["type"] for i in body["items"]}
    assert types == {"ADD", "DROP"}


def test_add_player_via_waiver_queues(authed_league, fake_session) -> None:
    w = authed_league.writer(1)
    w.add_player(500, scoring_period=115, via_waiver=True, bid_amount=5)
    _, body = fake_session.posts[-1]
    assert body["type"] == "WAIVER"
    assert body["executionType"] == "QUEUE"


def test_drop_player_only_has_drop_item(authed_league, fake_session) -> None:
    w = authed_league.writer(1)
    w.drop_player(102, scoring_period=115)
    _, body = fake_session.posts[-1]
    assert body["items"] == [{"playerId": 102, "type": "DROP"}]


def test_move_to_il_is_a_lineup_txn_with_il_slot(authed_league, fake_session) -> None:
    w = authed_league.writer(1)
    w.move_to_il(102, from_slot="BE", scoring_period=115)
    _, body = fake_session.posts[-1]
    assert body["type"] == "LINEUP"
    assert body["items"][0]["toLineupSlotId"] == 17


def test_move_off_il(authed_league, fake_session) -> None:
    w = authed_league.writer(1)
    w.move_off_il(102, to_slot="BE", scoring_period=115)
    _, body = fake_session.posts[-1]
    assert body["items"][0]["fromLineupSlotId"] == 17
    assert body["items"][0]["toLineupSlotId"] == 16


def test_propose_trade_legs_are_directional(authed_league, fake_session) -> None:
    w = authed_league.writer(1)
    w.propose_trade(to_team_id=2, offering=[100], requesting=[200, 201], expiration_days=3)
    _, body = fake_session.posts[-1]
    assert body["type"] == "TRADE_PROPOSAL"
    assert body["tradeExpirationHours"] == 72
    offered = [i for i in body["items"] if i["playerId"] == 100][0]
    assert offered["fromTeamId"] == 1 and offered["toTeamId"] == 2
    requested = [i for i in body["items"] if i["playerId"] == 200][0]
    assert requested["fromTeamId"] == 2 and requested["toTeamId"] == 1


def test_respond_to_trade(authed_league, fake_session) -> None:
    w = authed_league.writer(1)
    w.respond_to_trade(42, accept=True)
    _, body = fake_session.posts[-1]
    assert body["type"] == "TRADE_ACCEPT"
    assert body["tradeId"] == 42


def test_apply_plan_noops_when_no_changes(authed_league) -> None:
    from espn_fantasy_baseball import LineupPlan

    w = authed_league.writer(1)
    result = w.apply_plan(LineupPlan(moves=[], projected_total=0.0), scoring_period=115)
    assert result.ok is True
    assert result.status_code == 204


def test_apply_plan_submits_only_changed_moves(authed_league, fake_session) -> None:
    alice = authed_league.team(1)
    plan = authed_league.optimize_lineup(alice)
    w = authed_league.writer(1)
    w.apply_plan(plan, scoring_period=115)
    # At least one POST happened, provided the plan contained changes.
    if plan.changes():
        assert fake_session.posts, "expected plan.apply to POST lineup moves"
        _, body = fake_session.posts[-1]
        assert body["type"] == "LINEUP"
