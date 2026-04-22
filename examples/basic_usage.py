"""Quickstart: print a league's standings and the current week's matchups."""

from __future__ import annotations

import os

from espn_fantasy_baseball import League


def main() -> None:
    league_id = int(os.environ["LEAGUE_ID"])
    year = int(os.environ.get("SEASON", "2024"))

    lg = League(
        league_id=league_id,
        year=year,
        espn_s2=os.environ.get("ESPN_S2"),
        swid=os.environ.get("SWID"),
    )

    settings = lg.settings()
    print(f"=== {settings.name} ({settings.season}) — {settings.size}-team {settings.scoring_type} ===\n")

    print("Standings")
    for i, team in enumerate(lg.standings(), 1):
        print(f"  {i:>2}. {team.name:<30} {team.record:>7}  PF={team.points_for:>7.1f}")

    print("\nThis week's scoreboard")
    for m in lg.scoreboard():
        home = lg.team(m.home_team_id).name if m.home_team_id else "BYE"
        away = lg.team(m.away_team_id).name if m.away_team_id else "BYE"
        print(f"  {away:<25} {m.away_score:>7.1f}  @  {m.home_score:<7.1f} {home}")


if __name__ == "__main__":
    main()
