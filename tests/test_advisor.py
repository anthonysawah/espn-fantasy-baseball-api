"""Tests for the AI advisor (no network, no real Anthropic client)."""

from __future__ import annotations

from typing import Any

import pytest

from espn_fantasy_baseball.advisor import (
    AdviceReport,
    Advisor,
    AdvisorError,
)

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
