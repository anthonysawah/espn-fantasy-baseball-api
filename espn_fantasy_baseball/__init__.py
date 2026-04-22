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

from .analysis import (
    BoxscoreInsights,
    MatchupSummary,
    analyze_boxscore,
    close_games,
    longest_win_streak,
    strength_of_schedule,
    summarize_matchup,
)
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
from .optimizer import LineupMove, LineupPlan, optimize_lineup
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
from .writer import LeagueWriter, WriteResult

__version__ = "0.2.0"

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
    # optimizer
    "LineupMove",
    "LineupPlan",
    "optimize_lineup",
    # writer
    "LeagueWriter",
    "WriteResult",
    # analysis
    "MatchupSummary",
    "BoxscoreInsights",
    "summarize_matchup",
    "analyze_boxscore",
    "strength_of_schedule",
    "close_games",
    "longest_win_streak",
    # exceptions
    "ESPNFantasyError",
    "ESPNAPIError",
    "AuthenticationError",
    "PrivateLeagueError",
    "LeagueNotFoundError",
    "InvalidSeasonError",
    "__version__",
]
