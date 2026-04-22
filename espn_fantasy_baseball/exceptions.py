"""Exceptions raised by the ESPN Fantasy Baseball API client."""

from __future__ import annotations


class ESPNFantasyError(Exception):
    """Base class for all errors raised by this package."""


class AuthenticationError(ESPNFantasyError):
    """Raised for 401/403 responses – typically a missing or expired cookie."""


class PrivateLeagueError(AuthenticationError):
    """The requested league is private and credentials were not supplied / invalid."""


class LeagueNotFoundError(ESPNFantasyError):
    """The league id / season combination does not exist."""


class InvalidSeasonError(ESPNFantasyError):
    """The requested season is not supported (e.g. future seasons, pre-2018 history)."""


class ESPNAPIError(ESPNFantasyError):
    """A non-2xx response from ESPN that isn't covered by a more specific subclass."""

    def __init__(self, message: str, status_code: int | None = None, response_text: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text
