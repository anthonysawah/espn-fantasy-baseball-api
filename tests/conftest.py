"""Test fixtures shared across the suite."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import parse_qs, urlparse

import pytest

from espn_fantasy_baseball import ESPNClient, League

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict[str, Any]:
    with (FIXTURE_DIR / name).open() as f:
        return json.load(f)


class FakeResponse:
    """Minimal stand-in for :class:`requests.Response`."""

    def __init__(self, payload: Any, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload) if isinstance(payload, (dict, list)) else str(payload)
        self.headers: dict[str, str] = {}

    def json(self) -> Any:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class _FakeCookieJar(dict):
    """Minimal cookie jar supporting the ``.set`` and ``.get`` calls we use."""

    def set(self, name: str, value: str) -> None:
        self[name] = value

    def get(self, name: str, default: Any = None) -> Any:
        return super().get(name, default)


class FakeSession:
    """Session stub routing URLs to canned JSON payloads.

    The route map is keyed on the sorted ``view=`` query values joined by
    ``+`` (e.g. ``"mRoster+mTeam"``, in alphabetical order).  Requests
    without ``view`` params match the ``""`` key.
    """

    def __init__(self, route_map: Mapping[str, Any], *, default: Any = None):
        self.route_map = dict(route_map)
        self.default = default
        self.calls: list[tuple[str, str, Mapping[str, Any] | None]] = []
        self.cookies = _FakeCookieJar()
        self.headers: dict[str, str] = {}

    # Mimic the pieces of requests.Session that our code uses.
    def request(self, method: str, url: str, *, headers=None, json=None, timeout=None):  # noqa: ARG002
        self.calls.append((method, url, headers))
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        views = tuple(sorted(qs.get("view", [])))
        key = "+".join(views)
        payload = self.route_map.get(key, self.default)
        if payload is None:
            # Return an empty dict so callers that expect JSON don't crash.
            payload = {}
        if callable(payload):
            payload = payload(url, headers, qs)
        if isinstance(payload, FakeResponse):
            return payload
        return FakeResponse(payload)


@pytest.fixture
def fake_league() -> League:
    routes = {
        "mSettings": load_fixture("league_settings.json"),
        "mRoster+mTeam": load_fixture("league_teams.json"),
        "mTeam": load_fixture("league_teams.json"),
        "mStandings+mTeam": load_fixture("league_teams.json"),
        "mMatchup+mSchedule": load_fixture("league_schedule.json"),
        "mDraftDetail+mTeam": load_fixture("league_draft.json"),
        "kona_player_info+mPlayer": load_fixture("free_agents.json"),
        "mBoxscore+mMatchup+mRoster": load_fixture("boxscore.json"),
    }
    session = FakeSession(routes)
    client = ESPNClient(league_id=123456, year=2024, session=session)
    return League(league_id=123456, year=2024, client=client)
