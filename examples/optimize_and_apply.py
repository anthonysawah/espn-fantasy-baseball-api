"""Compute your team's best lineup and (optionally) submit it to ESPN.

Usage::

    LEAGUE_ID=123456 TEAM_ID=1 ESPN_S2=... SWID={...} python examples/optimize_and_apply.py
    # add --apply --period 115 to actually submit the moves
"""

from __future__ import annotations

import argparse
import os

from espn_fantasy_baseball import League


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Actually submit the moves")
    parser.add_argument("--period", type=int, default=None, help="Scoring period for --apply")
    args = parser.parse_args()

    lg = League(
        league_id=int(os.environ["LEAGUE_ID"]),
        year=int(os.environ.get("SEASON", "2024")),
        espn_s2=os.environ.get("ESPN_S2"),
        swid=os.environ.get("SWID"),
    )
    team_id = int(os.environ["TEAM_ID"])

    plan = lg.optimize_lineup(team_id)
    print(plan.summary())

    if args.apply:
        if args.period is None:
            raise SystemExit("--apply requires --period (the scoring period id)")
        result = lg.writer(team_id).apply_plan(plan, scoring_period=args.period)
        print(f"\nHTTP {result.status_code}  ok={result.ok}")


if __name__ == "__main__":
    main()
