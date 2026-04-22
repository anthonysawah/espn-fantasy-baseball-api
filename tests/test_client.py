"""Tests for the low-level HTTP client."""

from __future__ import annotations

import pytest

from espn_fantasy_baseball import ESPNClient
from espn_fantasy_baseball.exceptions import (
    ESPNAPIError,
    InvalidSeasonError,
    LeagueNotFoundError,
    PrivateLeagueError,
)

from .conftest import FakeResponse, FakeSession


def test_swid_is_braced_automatically() -> None:
    client = ESPNClient(1, 2024, swid="abc-123", espn_s2="x")
    assert client.swid == "{abc-123}"


def test_swid_already_braced_passes_through() -> None:
    client = ESPNClient(1, 2024, swid="{abc-123}", espn_s2="x")
    assert client.swid == "{abc-123}"


def test_cookies_are_attached_when_both_present() -> None:
    client = ESPNClient(1, 2024, swid="abc", espn_s2="xyz")
    assert client.session.cookies.get("espn_s2") == "xyz"
    assert client.session.cookies.get("SWID") == "{abc}"


def test_cookies_are_not_attached_when_missing() -> None:
    client = ESPNClient(1, 2024)
    assert client.session.cookies.get("espn_s2") is None
    assert client.session.cookies.get("SWID") is None


def test_url_current_season() -> None:
    client = ESPNClient(42, 2026)
    assert "/seasons/2026/segments/0/leagues/42" in client._url_current()


def test_url_history_includes_season_param() -> None:
    client = ESPNClient(42, 2019)
    url = client._url_history()
    assert url.endswith("/42?seasonId=2019")


def test_get_composes_view_query_params() -> None:
    # FakeSession matches on alphabetically-sorted view names.
    session = FakeSession({"mRoster+mTeam": {"ok": True}})
    client = ESPNClient(1, 2024, session=session)
    result = client.get(views=["mTeam", "mRoster"])
    assert result == {"ok": True}
    _, url, _ = session.calls[0]
    assert "view=mTeam" in url
    assert "view=mRoster" in url


def test_401_without_cookies_is_private_league() -> None:
    session = FakeSession({"": FakeResponse({"error": "nope"}, status_code=401)})
    client = ESPNClient(1, 2024, session=session, max_retries=0)
    with pytest.raises(PrivateLeagueError):
        client.get()


def test_401_with_cookies_is_still_private_league_error() -> None:
    session = FakeSession({"": FakeResponse({"error": "nope"}, status_code=403)})
    client = ESPNClient(1, 2024, session=session, swid="{x}", espn_s2="y", max_retries=0)
    with pytest.raises(PrivateLeagueError):
        client.get()


def test_404_raises_league_not_found() -> None:
    session = FakeSession({"": FakeResponse({}, status_code=404)})
    client = ESPNClient(1, 2024, session=session, max_retries=0)
    with pytest.raises(LeagueNotFoundError):
        client.get()


def test_400_raises_invalid_season() -> None:
    session = FakeSession({"": FakeResponse({}, status_code=400)})
    client = ESPNClient(1, 2024, session=session, max_retries=0)
    with pytest.raises(InvalidSeasonError):
        client.get()


def test_non_json_response_raises_api_error() -> None:
    session = FakeSession({"": FakeResponse(ValueError("not json"), status_code=200)})
    client = ESPNClient(1, 2024, session=session, max_retries=0)
    with pytest.raises(ESPNAPIError):
        client.get()


def test_retries_on_503(monkeypatch) -> None:
    monkeypatch.setattr("espn_fantasy_baseball.client.time.sleep", lambda *_a, **_k: None)
    attempts: list[int] = []

    def handler(url, headers, qs):
        attempts.append(1)
        if len(attempts) < 3:
            return FakeResponse({}, status_code=503)
        return FakeResponse({"ok": True})

    session = FakeSession({"": handler})
    client = ESPNClient(1, 2024, session=session, max_retries=3)
    assert client.get() == {"ok": True}
    assert len(attempts) == 3
