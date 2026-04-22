"""Low-level HTTP client for the ESPN Fantasy Baseball API.

This module deliberately knows nothing about leagues, teams or players.  It
is responsible purely for:

* Building request URLs (current season vs. league-history).
* Attaching auth cookies (``SWID`` / ``espn_s2``) for private leagues.
* Composing ``view`` query parameters.
* Handling retries, rate limits, and translating HTTP errors into
  :mod:`espn_fantasy_baseball.exceptions` types.

Higher-level resources such as :class:`espn_fantasy_baseball.League` build on
top of :class:`ESPNClient`.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Iterable, Mapping

import requests

from .constants import (
    DEFAULT_USER_AGENT,
    FANTASY_HISTORICAL_BASE,
    FANTASY_READ_BASE,
)
from .exceptions import (
    ESPNAPIError,
    InvalidSeasonError,
    LeagueNotFoundError,
    PrivateLeagueError,
)

log = logging.getLogger(__name__)

_RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})


class ESPNClient:
    """Thin wrapper around :mod:`requests` for ESPN Fantasy Baseball.

    Parameters
    ----------
    league_id:
        The numeric league id (found in the URL of your league page).
    year:
        The fantasy season (e.g. ``2024``).
    espn_s2, swid:
        Authentication cookies for private leagues.  Both are required
        together.  You can copy them from your browser's dev-tools after
        logging in to espn.com.
    session:
        Optional pre-configured :class:`requests.Session`.  A new session is
        created if not supplied.
    timeout:
        Per-request timeout in seconds.
    max_retries:
        Number of times to retry on 429/5xx responses.
    user_agent:
        Override the default ``User-Agent`` header.
    """

    def __init__(
        self,
        league_id: int,
        year: int,
        *,
        espn_s2: str | None = None,
        swid: str | None = None,
        session: requests.Session | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        self.league_id = int(league_id)
        self.year = int(year)
        self.espn_s2 = espn_s2
        self.swid = self._normalize_swid(swid) if swid else None
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = session or requests.Session()
        self.session.headers.setdefault("User-Agent", user_agent)
        self.session.headers.setdefault("Accept", "application/json")
        if self.espn_s2 and self.swid:
            self.session.cookies.set("espn_s2", self.espn_s2)
            self.session.cookies.set("SWID", self.swid)

    # ------------------------------------------------------------------
    # URL construction
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_swid(swid: str) -> str:
        """Ensure the SWID is wrapped in braces (``{...}``) as ESPN expects."""
        swid = swid.strip()
        if not swid.startswith("{"):
            swid = "{" + swid
        if not swid.endswith("}"):
            swid = swid + "}"
        return swid

    def _is_historical(self) -> bool:
        """Historical-league-history is used for past seasons.

        ESPN treats seasons before ~2018 differently — the current-season
        endpoint only has data for the active season and a handful of prior
        ones, so we route older requests through the league-history URL.
        """
        # We don't know today's season at runtime without an extra call, so
        # we rely on a simple heuristic: if the season is older than three
        # years behind an optimistic "now", use history.  Callers who want
        # to force one or the other should use :meth:`_url_current` /
        # :meth:`_url_history` directly.
        import datetime as _dt

        return self.year < _dt.date.today().year - 2

    def _url_current(self) -> str:
        return (
            f"{FANTASY_READ_BASE}/seasons/{self.year}/segments/0/leagues/{self.league_id}"
        )

    def _url_history(self) -> str:
        return f"{FANTASY_HISTORICAL_BASE}/{self.league_id}?seasonId={self.year}"

    def url(self) -> str:
        """Return the correct base URL for this season."""
        return self._url_history() if self._is_historical() else self._url_current()

    # ------------------------------------------------------------------
    # Request
    # ------------------------------------------------------------------

    def get(
        self,
        *,
        views: Iterable[str] | None = None,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        path: str = "",
    ) -> Any:
        """Issue a GET against the league endpoint.

        Parameters
        ----------
        views:
            One or more ESPN ``view`` values to compose (e.g. ``["mTeam", "mRoster"]``).
        params:
            Extra query parameters.
        headers:
            Extra request headers (commonly ``X-Fantasy-Filter`` for player queries).
        path:
            Optional path suffix appended to the base league URL (e.g. ``/players``).
        """
        base = self.url()
        # The historical URL already includes a query string (``?seasonId=...``).
        joiner = "&" if "?" in base else "?"

        query_parts: list[str] = []
        if views:
            query_parts.extend(f"view={v}" for v in views)
        if params:
            for k, v in params.items():
                query_parts.append(f"{k}={v}")

        url = base
        if path:
            # Insert the path before the query string.
            if "?" in base:
                head, sep, tail = base.partition("?")
                url = f"{head}{path}{sep}{tail}"
            else:
                url = f"{base}{path}"

        if query_parts:
            url = f"{url}{joiner}{'&'.join(query_parts)}"

        return self._request("GET", url, headers=headers)

    def _request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        json: Any = None,
    ) -> Any:
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(
                    method,
                    url,
                    headers=dict(headers) if headers else None,
                    json=json,
                    timeout=self.timeout,
                )
            except requests.RequestException as exc:  # network-level failure
                last_exc = exc
                if attempt >= self.max_retries:
                    raise ESPNAPIError(f"Network error contacting ESPN: {exc}") from exc
                self._backoff(attempt)
                continue

            if response.status_code in _RETRY_STATUSES and attempt < self.max_retries:
                log.debug(
                    "ESPN returned %s; retrying (%s/%s)",
                    response.status_code,
                    attempt + 1,
                    self.max_retries,
                )
                self._backoff(attempt, retry_after=response.headers.get("Retry-After"))
                continue

            return self._handle_response(response)

        # Should be unreachable, but keep mypy happy.
        raise ESPNAPIError("Exhausted retries contacting ESPN") from last_exc

    def _handle_response(self, response: requests.Response) -> Any:
        status = response.status_code
        if 200 <= status < 300:
            try:
                return response.json()
            except ValueError as exc:
                raise ESPNAPIError(
                    "ESPN returned a non-JSON response",
                    status_code=status,
                    response_text=response.text[:500],
                ) from exc

        if status in (401, 403):
            # ESPN uses both for auth issues.  If we never sent cookies, it's
            # a private-league error; otherwise the cookies are likely stale.
            if not (self.espn_s2 and self.swid):
                raise PrivateLeagueError(
                    "League is private.  Supply espn_s2 and swid cookies."
                )
            raise PrivateLeagueError(
                "ESPN rejected your cookies (expired or invalid)."
            )

        if status == 404:
            raise LeagueNotFoundError(
                f"League {self.league_id} not found for season {self.year}."
            )

        if status == 400:
            # ESPN uses 400 for unsupported historical seasons.
            raise InvalidSeasonError(
                f"ESPN rejected season {self.year} for league {self.league_id} "
                f"(probably too old or not yet started)."
            )

        raise ESPNAPIError(
            f"ESPN returned HTTP {status}",
            status_code=status,
            response_text=response.text[:500],
        )

    @staticmethod
    def _backoff(attempt: int, retry_after: str | None = None) -> None:
        if retry_after:
            try:
                time.sleep(float(retry_after))
                return
            except ValueError:
                pass
        # Exponential backoff with a small floor: 0.5, 1, 2, 4 ...
        time.sleep(0.5 * (2**attempt))

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def __repr__(self) -> str:  # pragma: no cover
        auth = "authenticated" if self.espn_s2 and self.swid else "anonymous"
        return f"<ESPNClient league={self.league_id} year={self.year} {auth}>"
