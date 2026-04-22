"""High-level League facade — the primary entry point to the API.

Typical usage::

    from espn_fantasy_baseball import League

    lg = League(league_id=123456, year=2024, espn_s2="...", swid="{...}")
    for team in lg.teams():
        print(team.name, team.record)
"""

from __future__ import annotations

import json
from typing import Any, Iterable, Mapping

from .client import ESPNClient
from .constants import (
    VIEW_BOXSCORE,
    VIEW_DRAFT,
    VIEW_MATCHUP,
    VIEW_PLAYER,
    VIEW_ROSTER,
    VIEW_SCHEDULE,
    VIEW_SETTINGS,
    VIEW_STANDINGS,
    VIEW_TEAM,
    VIEW_TOPICS,
    VIEW_TRANSACTIONS,
)
from .resources import (
    Activity,
    Boxscore,
    DraftPick,
    LeagueSettings,
    Matchup,
    Player,
    Team,
)


class League:
    """User-facing entry point bundling every read-only ESPN endpoint.

    Calls are lazy: nothing is fetched until you call a method.  Results are
    cached per-``(league, season)`` so repeated calls in the same process
    don't re-hit ESPN.  Call :meth:`refresh` to invalidate the cache.
    """

    def __init__(
        self,
        league_id: int,
        year: int,
        *,
        espn_s2: str | None = None,
        swid: str | None = None,
        client: ESPNClient | None = None,
        **client_kwargs: Any,
    ) -> None:
        if client is not None:
            self._client = client
        else:
            self._client = ESPNClient(
                league_id=league_id,
                year=year,
                espn_s2=espn_s2,
                swid=swid,
                **client_kwargs,
            )
        self._cache: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    def league_id(self) -> int:
        return self._client.league_id

    @property
    def year(self) -> int:
        return self._client.year

    @property
    def client(self) -> ESPNClient:
        return self._client

    def refresh(self) -> None:
        """Drop the in-process cache so the next call re-fetches."""
        self._cache.clear()

    # ------------------------------------------------------------------
    # Raw / composite fetches
    # ------------------------------------------------------------------

    def _fetch(self, views: Iterable[str], *, cache_key: str | None = None) -> Any:
        key = cache_key or "+".join(views)
        if key in self._cache:
            return self._cache[key]
        data = self._client.get(views=list(views))
        # Historical endpoint returns a list; current endpoint a dict.  We
        # normalise to a dict by taking the first entry when we get a list.
        if isinstance(data, list) and data:
            data = data[0]
        self._cache[key] = data
        return data

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def settings(self) -> LeagueSettings:
        """Return the league's :class:`LeagueSettings`."""
        raw = self._fetch([VIEW_SETTINGS])
        return LeagueSettings.from_raw(raw)

    # ------------------------------------------------------------------
    # Teams & members
    # ------------------------------------------------------------------

    def _members_by_id(self) -> dict[str, Mapping[str, Any]]:
        raw = self._fetch([VIEW_TEAM])
        members = raw.get("members") or []
        return {m["id"]: m for m in members if m.get("id")}

    def teams(self) -> list[Team]:
        """All teams in the league, with basic record + owner info."""
        raw = self._fetch([VIEW_TEAM, VIEW_ROSTER])
        members = self._members_by_id()
        return [Team.from_raw(t, members_by_id=members) for t in (raw.get("teams") or [])]

    def team(self, team_id: int) -> Team:
        """Single team by id."""
        for team in self.teams():
            if team.id == team_id:
                return team
        raise KeyError(f"No team with id={team_id} in league {self.league_id}")

    def standings(self) -> list[Team]:
        """Teams ordered by current standings (best record first)."""
        raw = self._fetch([VIEW_STANDINGS, VIEW_TEAM])
        members = self._members_by_id()
        teams = [Team.from_raw(t, members_by_id=members) for t in (raw.get("teams") or [])]
        teams.sort(key=_standings_sort_key)
        return teams

    # ------------------------------------------------------------------
    # Schedule / matchups / boxscores
    # ------------------------------------------------------------------

    def schedule(self) -> list[Matchup]:
        """Full season schedule (regular season + playoffs)."""
        raw = self._fetch([VIEW_MATCHUP, VIEW_SCHEDULE])
        return [Matchup.from_raw(m) for m in (raw.get("schedule") or [])]

    def matchups(self, matchup_period: int) -> list[Matchup]:
        """All matchups for a given scoring period."""
        return [m for m in self.schedule() if m.matchup_period == matchup_period]

    def scoreboard(self, matchup_period: int | None = None) -> list[Matchup]:
        """Alias for :meth:`matchups` with a sane default (current period)."""
        if matchup_period is None:
            raw = self._fetch([VIEW_MATCHUP, VIEW_SCHEDULE])
            status = raw.get("status") or {}
            matchup_period = status.get("currentMatchupPeriod", 1)
        return self.matchups(matchup_period)

    def boxscores(self, matchup_period: int) -> list[Boxscore]:
        """Boxscores (including rosters + per-player stats) for a period."""
        # The boxscore view needs ?scoringPeriodId so ESPN includes rosters.
        data = self._client.get(
            views=[VIEW_BOXSCORE, VIEW_MATCHUP, VIEW_ROSTER],
            params={"scoringPeriodId": matchup_period, "matchupPeriodId": matchup_period},
        )
        if isinstance(data, list) and data:
            data = data[0]
        return [
            Boxscore.from_raw(m)
            for m in (data.get("schedule") or [])
            if m.get("matchupPeriodId") == matchup_period
        ]

    # ------------------------------------------------------------------
    # Draft
    # ------------------------------------------------------------------

    def draft(self) -> list[DraftPick]:
        """All picks from the draft in overall-pick order."""
        raw = self._fetch([VIEW_DRAFT, VIEW_TEAM])
        picks = (raw.get("draftDetail") or {}).get("picks") or []
        # Try to resolve names from the ``players`` section if ESPN included it.
        names: dict[int, str] = {}
        for p in raw.get("players") or []:
            info = p.get("player") if isinstance(p, dict) and "player" in p else p
            pid = info.get("id") if isinstance(info, dict) else None
            if pid is not None:
                names[int(pid)] = info.get("fullName") or ""
        return [DraftPick.from_raw(p, player_names=names) for p in picks]

    # ------------------------------------------------------------------
    # Free agents / players
    # ------------------------------------------------------------------

    def free_agents(
        self,
        *,
        size: int = 50,
        position: str | None = None,
        sort_by: str = "percent_owned",
        scoring_period: int | None = None,
    ) -> list[Player]:
        """List the top free agents by ownership (or custom sort).

        Parameters
        ----------
        size:
            Number of players to return (max 1000).
        position:
            Filter to a position abbreviation (e.g. ``"SS"``, ``"SP"``).
        sort_by:
            One of ``"percent_owned"`` (default), ``"percent_started"``,
            ``"season_points"`` or ``"last7_points"``.
        scoring_period:
            Optional scoring period for ``last7_points`` sorting.
        """
        filter_payload = _free_agent_filter(
            size=size, position=position, sort_by=sort_by
        )
        headers = {"X-Fantasy-Filter": json.dumps(filter_payload)}
        params: dict[str, Any] = {}
        if scoring_period is not None:
            params["scoringPeriodId"] = scoring_period
        data = self._client.get(
            views=[VIEW_PLAYER, VIEW_TOPICS],
            params=params or None,
            headers=headers,
        )
        if isinstance(data, list) and data:
            data = data[0]
        pool = data.get("players") or []
        return [Player.from_player_pool(p) for p in pool]

    def player_by_id(self, player_id: int) -> Player | None:
        """Fetch a single player by their ESPN id.  Returns ``None`` if not found."""
        filter_payload = {
            "players": {
                "filterIds": {"value": [int(player_id)]},
                "limit": 1,
            }
        }
        headers = {"X-Fantasy-Filter": json.dumps(filter_payload)}
        data = self._client.get(views=[VIEW_PLAYER], headers=headers)
        if isinstance(data, list) and data:
            data = data[0]
        pool = data.get("players") or []
        if not pool:
            return None
        return Player.from_player_pool(pool[0])

    # ------------------------------------------------------------------
    # Transactions / activity
    # ------------------------------------------------------------------

    def recent_activity(self, *, size: int = 25) -> list[Activity]:
        """The league's most recent activity feed (adds, drops, trades)."""
        filter_payload = {"topics": {"limit": size, "filterType": {"value": ["ACTIVITY_TRANSACTIONS"]}}}
        headers = {"X-Fantasy-Filter": json.dumps(filter_payload)}
        data = self._client.get(views=[VIEW_TRANSACTIONS, VIEW_TOPICS], headers=headers)
        if isinstance(data, list) and data:
            data = data[0]
        topics = (data.get("topics") or [])
        return [Activity.from_raw(t) for t in topics]

    # ------------------------------------------------------------------
    # Convenience: power rankings
    # ------------------------------------------------------------------

    def power_rankings(self, *, weights: Mapping[str, float] | None = None) -> list[tuple[Team, float]]:
        """Compute a simple blended power ranking for each team.

        The default formula is ``0.7 * points_for + 0.3 * win_pct * max_points_for``
        which tends to correlate well with end-of-season standings.  Callers
        can override via ``weights`` (keys: ``"points_for"``, ``"win_pct"``).
        """
        teams = self.teams()
        if not teams:
            return []
        w = dict(weights or {})
        w_pf = w.get("points_for", 0.7)
        w_wp = w.get("win_pct", 0.3)
        max_pf = max((t.points_for for t in teams), default=1.0) or 1.0

        def _score(t: Team) -> float:
            games = t.wins + t.losses + t.ties
            win_pct = (t.wins + 0.5 * t.ties) / games if games else 0.0
            return w_pf * t.points_for + w_wp * win_pct * max_pf

        ranked = sorted(((t, _score(t)) for t in teams), key=lambda p: p[1], reverse=True)
        return ranked

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:  # pragma: no cover
        return f"League(id={self.league_id}, year={self.year})"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _standings_sort_key(team: Team) -> tuple[float, float]:
    """Rank by (desc) win pct, then by (desc) points-for."""
    games = team.wins + team.losses + team.ties
    win_pct = (team.wins + 0.5 * team.ties) / games if games else 0.0
    return (-win_pct, -team.points_for)


_POSITION_FILTER_MAP = {
    # Maps our abbreviations → ESPN slot ids for the `filterSlotIds` filter.
    "C": [0],
    "1B": [1],
    "2B": [2],
    "3B": [3],
    "SS": [4],
    "OF": [5],
    "DH": [11],
    "UTIL": [12],
    "P": [13, 14, 15],
    "SP": [14],
    "RP": [15],
}


_SORT_KEY_MAP = {
    "percent_owned": "sortPercOwned",
    "percent_started": "sortPercStarted",
    "season_points": "sortAppliedStatTotal",
    "last7_points": "sortAppliedStatTotal7Days",
}


def _free_agent_filter(*, size: int, position: str | None, sort_by: str) -> dict[str, Any]:
    sort_key = _SORT_KEY_MAP.get(sort_by, "sortPercOwned")
    players_filter: dict[str, Any] = {
        "filterStatus": {"value": ["FREEAGENT", "WAIVERS"]},
        "limit": int(size),
        sort_key: {"sortPriority": 1, "sortAsc": False},
    }
    if position and position in _POSITION_FILTER_MAP:
        players_filter["filterSlotIds"] = {"value": _POSITION_FILTER_MAP[position]}
    return {"players": players_filter}
