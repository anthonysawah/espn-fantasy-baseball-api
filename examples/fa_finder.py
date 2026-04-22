"""Find the best-owned free agents at a given position."""

from __future__ import annotations

import argparse
import os

from espn_fantasy_baseball import League


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--position", default="SS")
    parser.add_argument("--size", type=int, default=25)
    args = parser.parse_args()

    lg = League(
        league_id=int(os.environ["LEAGUE_ID"]),
        year=int(os.environ.get("SEASON", "2024")),
        espn_s2=os.environ.get("ESPN_S2"),
        swid=os.environ.get("SWID"),
    )

    players = lg.free_agents(size=args.size, position=args.position)
    width = max((len(p.name) for p in players), default=10)
    print(f"Top {len(players)} free agents at {args.position}")
    for p in players:
        positions = "/".join(p.eligible_positions) or "?"
        injury = f" [{p.injury_status}]" if p.injury_status and p.injury_status != "Active" else ""
        print(f"  {p.name:<{width}}  {p.pro_team:<4}  {positions:<10}  owned={p.percent_owned:5.1f}%{injury}")


if __name__ == "__main__":
    main()
