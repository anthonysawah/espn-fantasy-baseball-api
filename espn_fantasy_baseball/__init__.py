"""espn-fantasy-baseball-api: a modern Python client for the ESPN Fantasy Baseball API.

Example
-------

>>> from espn_fantasy_baseball import League
>>> lg = League(league_id=123456, year=2024)
>>> for team in lg.standings():
...     print(team.standings_rank, team.name, team.record)

For private leagues pass ``espn_s2`` and ``swid`` cookies::

>>> lg = League(123456, 2024, espn_s2="...", swid="{ABC-...}")
"""

from __future__ import annotations

from .client import ESPNClient
from .exceptions import (
    AuthenticationError,
    ESPNAPIError,
    ESPNFantasyError,
    InvalidSeasonError,
    LeagueNotFoundError,
    PrivateLeagueError,
)
from .league import League
from .resources import (
    Activity,
    ActivityAction,
    Boxscore,
    BoxscorePlayer,
    DraftPick,
    LeagueSettings,
    Matchup,
    Player,
    PlayerStats,
    ScoringItem,
    Team,
)

__version__ = "0.1.0"

__all__ = [
    "League",
    "ESPNClient",
    # resources
    "Team",
    "Player",
    "PlayerStats",
    "Matchup",
    "Boxscore",
    "BoxscorePlayer",
    "DraftPick",
    "Activity",
    "ActivityAction",
    "LeagueSettings",
    "ScoringItem",
    # exceptions
    "ESPNFantasyError",
    "ESPNAPIError",
    "AuthenticationError",
    "PrivateLeagueError",
    "LeagueNotFoundError",
    "InvalidSeasonError",
    "__version__",
]
