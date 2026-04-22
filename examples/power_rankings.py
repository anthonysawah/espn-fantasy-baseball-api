"""Print a simple blended power ranking for every team in your league."""

from __future__ import annotations

import os

from espn_fantasy_baseball import League


def main() -> None:
    lg = League(
        league_id=int(os.environ["LEAGUE_ID"]),
        year=int(os.environ.get("SEASON", "2024")),
        espn_s2=os.environ.get("ESPN_S2"),
        swid=os.environ.get("SWID"),
    )

    # Default weights are 0.7 * PF + 0.3 * win_pct * max(PF).  Tweak as you like.
    rankings = lg.power_rankings(weights={"points_for": 0.65, "win_pct": 0.35})

    width = max(len(t.name) for t, _ in rankings) if rankings else 10
    print(f"{'#':>2}  {'Team':<{width}}  {'Score':>7}  {'Record':>8}  {'PF':>8}")
    for i, (team, score) in enumerate(rankings, 1):
        print(f"{i:>2}  {team.name:<{width}}  {score:>7.2f}  {team.record:>8}  {team.points_for:>8.1f}")


if __name__ == "__main__":
    main()
