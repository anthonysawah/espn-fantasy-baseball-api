"""CLI tests — monkeypatch ``League`` so no HTTP happens."""

from __future__ import annotations

import pytest

from espn_fantasy_baseball import cli


@pytest.fixture
def patched_cli(monkeypatch, fake_league):
    def fake_league_from_args(args):
        return fake_league
    monkeypatch.setattr(cli, "_league_from_args", fake_league_from_args)
    return fake_league


def test_standings_command_prints_all_teams(patched_cli, capsys) -> None:
    rc = cli.main(["standings", "--league", "1", "--year", "2024"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Alice's Aces" in out
    assert "Bob's Bombers" in out
    assert "12-5-1" in out


def test_roster_command(patched_cli, capsys) -> None:
    rc = cli.main(["roster", "--league", "1", "--year", "2024", "--team", "1"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Catcher Clyde" in out
    assert "Ace Anderson" in out


def test_matchups_command(patched_cli, capsys) -> None:
    rc = cli.main(["matchups", "--league", "1", "--year", "2024", "--week", "1"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Alice's Aces" in out


def test_power_command(patched_cli, capsys) -> None:
    rc = cli.main(["power", "--league", "1", "--year", "2024"])
    assert rc == 0
    out = capsys.readouterr().out
    # Alice is the clear #1 by both PF and record
    lines = [line for line in out.splitlines() if line.strip()]
    assert "Alice's Aces" in lines[0]


def test_draft_command(patched_cli, capsys) -> None:
    rc = cli.main(["draft", "--league", "1", "--year", "2024"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Ace Anderson" in out
    assert "$55" in out


def test_settings_command(patched_cli, capsys) -> None:
    rc = cli.main(["settings", "--league", "1", "--year", "2024"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "The Show" in out
    assert "H2H_POINTS" in out
