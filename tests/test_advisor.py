"""Tests for the AI advisor (no network, no real Anthropic client)."""

from __future__ import annotations

from typing import Any

import pytest

from espn_fantasy_baseball import ESPNClient, League
from espn_fantasy_baseball.advisor import (
    AdviceReport,
    Advisor,
    AdvisorError,
    _drop_ranking_block,
    _fetch_player_news,
    _news_section,
    _trend,
)
from espn_fantasy_baseball.resources import Player, PlayerStats, Team

from .conftest import FakeSession, _default_routes

# ---------------------------------------------------------------------------
# Fake Anthropic client
# ---------------------------------------------------------------------------


class FakeTextBlock:
    type = "text"

    def __init__(self, text: str):
        self.text = text


class FakeUsage:
    input_tokens = 1200
    output_tokens = 340


class FakeMessage:
    def __init__(self, text: str, stop_reason: str = "end_turn"):
        self.content = [FakeTextBlock(text)]
        self.stop_reason = stop_reason
        self.usage = FakeUsage()


class FakeStream:
    def __init__(self, message: FakeMessage):
        self._message = message

    def __enter__(self) -> FakeStream:
        return self

    def __exit__(self, *exc: Any) -> None:
        pass

    def get_final_message(self) -> FakeMessage:
        return self._message


class FakeMessages:
    def __init__(self, message: FakeMessage):
        self._message = message
        self.calls: list[dict[str, Any]] = []

    def stream(self, **kwargs: Any) -> FakeStream:
        self.calls.append(kwargs)
        return FakeStream(self._message)


class FakeAnthropic:
    def __init__(self, text: str = "## TL;DR\n- Add Free Agent One", stop_reason: str = "end_turn"):
        self.messages = FakeMessages(FakeMessage(text, stop_reason=stop_reason))


# ---------------------------------------------------------------------------
# Context building
# ---------------------------------------------------------------------------


def test_build_context_includes_league_and_roster(fake_league):
    advisor = Advisor(fake_league, team_id=1, anthropic_client=FakeAnthropic())
    context = advisor.build_context()
    assert "# LEAGUE" in context
    assert "# STANDINGS" in context
    assert "<-- YOUR TEAM" in context
    assert "Alice's Aces" in context
    assert "# YOUR ROSTER" in context
    assert "# FREE AGENTS" in context
    assert "Free Agent One" in context


def test_build_context_marks_correct_team(fake_league):
    advisor = Advisor(fake_league, team_id=2, anthropic_client=FakeAnthropic())
    context = advisor.build_context()
    marked = [line for line in context.splitlines() if "<-- YOUR TEAM" in line]
    assert len(marked) == 1
    assert "Bob's Bombers" in marked[0]


def test_build_context_includes_timeline(fake_league):
    advisor = Advisor(fake_league, team_id=1, anthropic_client=FakeAnthropic())
    context = advisor.build_context()
    assert "Today: " in context


NEWS_PAYLOAD = {
    "news": {
        "feed": [
            {
                "headline": "Rooker ruled out for the season.",
                "story": "Rooker underwent knee surgery and is expected back for spring training.",
                "published": "2026-07-17T20:33:39Z",
            }
        ]
    }
}


def _news_league() -> League:
    routes = _default_routes()
    routes[""] = NEWS_PAYLOAD  # requests without ?view= (the news endpoint)
    session = FakeSession(routes)
    client = ESPNClient(league_id=123456, year=2024, session=session)
    return League(league_id=123456, year=2024, client=client)


def test_fetch_player_news_returns_lines():
    lg = _news_league()
    lines = _fetch_player_news(lg, 40926)
    assert len(lines) == 1
    assert "Rooker ruled out for the season." in lines[0]
    assert "[2026-07-17]" in lines[0]


def test_news_section_covers_injured_roster_players():
    lg = _news_league()
    injured = Player(id=40926, name="Brent Rooker", pro_team="OAK", injury_status="60-Day IL")
    healthy = Player(id=1, name="Healthy Guy", pro_team="NYY", injury_status="ACTIVE")
    team = Team(id=1, abbreviation="T", name="Test", roster=[injured, healthy])
    section = _news_section(lg, team, fa_lists=[])
    assert "# PLAYER NEWS" in section
    assert "Brent Rooker (60-Day IL)" in section
    assert "spring training" in section
    assert "Healthy Guy" not in section


def test_news_section_empty_when_no_injuries():
    lg = _news_league()
    team = Team(id=1, abbreviation="T", name="Test", roster=[
        Player(id=1, name="Healthy Guy", pro_team="NYY", injury_status="ACTIVE"),
    ])
    assert _news_section(lg, team, fa_lists=[]) == ""


def test_system_prompt_covers_scarcity_and_injury_timelines(fake_league):
    client = FakeAnthropic()
    Advisor(fake_league, team_id=1, anthropic_client=client).advise()
    (call,) = client.messages.calls
    assert "PERMANENT" in call["system"]
    assert "claim risk" in call["system"]
    assert "PLAYER NEWS" in call["system"]


def _player_with_splits(name: str, *, last7: float, last30: float, proj: float | None = None,
                        season: float = 0.0, pid: int = 1) -> Player:
    stats = [
        PlayerStats(season=2024, source="real", split="last_7", applied_total=last7),
        PlayerStats(season=2024, source="real", split="last_30", applied_total=last30),
        PlayerStats(season=2024, source="real", split="season", applied_total=season),
    ]
    if proj is not None:
        stats.append(PlayerStats(season=2024, source="projected", split="season", applied_total=proj))
    return Player(id=pid, name=name, pro_team="NYY", stats=stats)


def test_trend_labels_are_computed_not_eyeballed():
    # 16 of 21 pts in the last 7 days: warming up, whatever the 30-day total looks like.
    assert _trend(_player_with_splits("Jeffers", last7=16, last30=21)) == "heating"
    # Big month, dead week: cooling.
    assert _trend(_player_with_splits("Cold", last7=0, last30=80)) == "cooling"
    # Evenly spread production: steady.
    assert _trend(_player_with_splits("Steady", last7=14, last30=60)) == "steady"
    # Nothing at all (e.g. long-term IL): quiet.
    assert _trend(_player_with_splits("Hurt", last7=0, last30=0)) == "quiet"
    # No split data: no label.
    assert _trend(Player(id=9, name="Nobody", pro_team="NYY")) is None


def test_drop_ranking_orders_by_rest_of_season_value():
    team = Team(id=1, abbreviation="T", name="Test", roster=[
        _player_with_splits("Star", last7=10, last30=40, proj=400, season=500, pid=1),
        _player_with_splits("Scrub", last7=0, last30=2, proj=50, season=60, pid=2),
        # Hot rookie without a projection must rank by season points, not zero.
        _player_with_splits("Rookie", last7=30, last30=90, proj=None, season=150, pid=3),
    ])
    lines = _drop_ranking_block(team)
    assert "Computed drop-candidate ranking" in lines[0]
    order = [line.split(". ")[1].split(" —")[0] for line in lines[1:]]
    assert order == ["Scrub", "Rookie", "Star"]
    assert "trend=heating" in lines[2]  # the rookie's hot streak is visible


def test_roster_section_contains_drop_ranking(fake_league):
    advisor = Advisor(fake_league, team_id=1, anthropic_client=FakeAnthropic(), preferences="")
    assert "Computed drop-candidate ranking" in advisor.build_context()


def test_system_prompt_contains_verification_checklist(fake_league):
    client = FakeAnthropic()
    Advisor(fake_league, team_id=1, anthropic_client=client, preferences="").advise()
    (call,) = client.messages.calls
    assert "verification checklist" in call["system"]
    assert "manufacture a drop" in call["system"].lower()


def test_preferences_included_and_marked_binding(fake_league):
    advisor = Advisor(
        fake_league, team_id=1, anthropic_client=FakeAnthropic(),
        preferences="Never drop Kyle Teel.",
    )
    context = advisor.build_context()
    assert "# MANAGER PREFERENCES (must be respected)" in context
    assert "Never drop Kyle Teel." in context
    # The system prompt must instruct the model to honor them.
    advisor.advise()
    (call,) = advisor._client.messages.calls
    assert "MANAGER PREFERENCES" in call["system"]


def test_preferences_file_autoloaded(fake_league, tmp_path, monkeypatch):
    (tmp_path / Advisor.PREFERENCES_FILE).write_text("Protect Player X.")
    monkeypatch.chdir(tmp_path)
    advisor = Advisor(fake_league, team_id=1, anthropic_client=FakeAnthropic())
    assert advisor.preferences == "Protect Player X."


def test_preferences_absent_when_no_file(fake_league, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    advisor = Advisor(fake_league, team_id=1, anthropic_client=FakeAnthropic())
    assert advisor.preferences is None
    assert "# MANAGER PREFERENCES" not in advisor.build_context()


def test_build_context_includes_free_agent_stats(fake_league):
    advisor = Advisor(fake_league, team_id=1, anthropic_client=FakeAnthropic())
    context = advisor.build_context()
    # Free Agent One has a season appliedTotal of 210.0 in the fixture.
    assert "season_pts=210.0" in context


# ---------------------------------------------------------------------------
# advise()
# ---------------------------------------------------------------------------


def test_advise_returns_report(fake_league):
    client = FakeAnthropic()
    advisor = Advisor(fake_league, team_id=1, anthropic_client=client)
    report = advisor.advise()

    assert isinstance(report, AdviceReport)
    assert "Free Agent One" in report.markdown
    assert report.model == "claude-opus-4-8"
    assert report.usage == {"input_tokens": 1200, "output_tokens": 340}

    (call,) = client.messages.calls
    assert call["model"] == "claude-opus-4-8"
    assert call["thinking"] == {"type": "adaptive"}
    assert "fantasy baseball" in call["system"]
    # The user prompt must carry the league snapshot.
    assert "# YOUR ROSTER" in call["messages"][0]["content"]


def test_advise_passes_focus(fake_league):
    client = FakeAnthropic()
    advisor = Advisor(fake_league, team_id=1, anthropic_client=client)
    advisor.advise(focus="I need saves")
    (call,) = client.messages.calls
    assert "I need saves" in call["messages"][0]["content"]


def test_advise_custom_model(fake_league):
    client = FakeAnthropic()
    advisor = Advisor(fake_league, team_id=1, model="claude-sonnet-5", anthropic_client=client)
    report = advisor.advise()
    assert report.model == "claude-sonnet-5"
    assert client.messages.calls[0]["model"] == "claude-sonnet-5"


def test_advise_raises_on_refusal(fake_league):
    client = FakeAnthropic(stop_reason="refusal")
    advisor = Advisor(fake_league, team_id=1, anthropic_client=client)
    with pytest.raises(AdvisorError):
        advisor.advise()


def test_advise_raises_on_empty_report(fake_league):
    client = FakeAnthropic(text="   ")
    advisor = Advisor(fake_league, team_id=1, anthropic_client=client)
    with pytest.raises(AdvisorError):
        advisor.advise()
