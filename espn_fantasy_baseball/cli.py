"""A small command-line interface.

Usage examples::

    espn-fb standings --league 123456 --year 2024
    espn-fb roster   --league 123456 --year 2024 --team 3
    espn-fb matchups --league 123456 --year 2024 --week 12
    espn-fb fa       --league 123456 --year 2024 --position SS --size 20
    espn-fb draft    --league 123456 --year 2024
    espn-fb power    --league 123456 --year 2024

Private leagues need ``--espn-s2`` and ``--swid`` (or the env vars
``ESPN_S2`` and ``SWID``).
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Sequence

from . import League, __version__
from .exceptions import ESPNFantasyError


def _league_from_args(args: argparse.Namespace) -> League:
    return League(
        league_id=args.league,
        year=args.year,
        espn_s2=args.espn_s2 or os.environ.get("ESPN_S2"),
        swid=args.swid or os.environ.get("SWID"),
    )


def _cmd_standings(args: argparse.Namespace) -> int:
    lg = _league_from_args(args)
    teams = lg.standings()
    width = max((len(t.name) for t in teams), default=10)
    print(f"{'#':>2}  {'Team':<{width}}  {'W-L-T':>7}  {'PF':>8}  {'PA':>8}")
    for i, t in enumerate(teams, 1):
        print(f"{i:>2}  {t.name:<{width}}  {t.record:>7}  {t.points_for:>8.1f}  {t.points_against:>8.1f}")
    return 0


def _cmd_roster(args: argparse.Namespace) -> int:
    lg = _league_from_args(args)
    team = lg.team(args.team)
    print(f"{team.name}  ({team.record})")
    width = max((len(p.name) for p in team.roster), default=10)
    for p in team.roster:
        positions = "/".join(p.eligible_positions) or "?"
        print(f"  {(p.lineup_slot or '-'):<5} {p.name:<{width}}  {p.pro_team:<4}  {positions}")
    return 0


def _cmd_matchups(args: argparse.Namespace) -> int:
    lg = _league_from_args(args)
    matchups = lg.matchups(args.week)
    if not matchups:
        print(f"No matchups for week {args.week}")
        return 1
    for m in matchups:
        home = lg.team(m.home_team_id).name if m.home_team_id else "BYE"
        away = lg.team(m.away_team_id).name if m.away_team_id else "BYE"
        print(f"  {away:>25} {m.away_score:>7.1f}  @  {m.home_score:<7.1f} {home}")
    return 0


def _cmd_fa(args: argparse.Namespace) -> int:
    lg = _league_from_args(args)
    players = lg.free_agents(size=args.size, position=args.position)
    width = max((len(p.name) for p in players), default=10)
    for p in players:
        positions = "/".join(p.eligible_positions) or "?"
        print(f"  {p.name:<{width}}  {p.pro_team:<4}  {positions:<10}  owned={p.percent_owned:5.1f}%")
    return 0


def _cmd_draft(args: argparse.Namespace) -> int:
    lg = _league_from_args(args)
    picks = lg.draft()
    if not picks:
        print("No draft data available.")
        return 1
    for p in picks:
        label = p.player_name or f"player#{p.player_id}"
        bid = f"${p.bid_amount}" if p.bid_amount is not None else ""
        print(f"  R{p.round:>2}.{p.round_pick:<2} (#{p.overall_pick:>3})  team={p.team_id}  {label}  {bid}")
    return 0


def _cmd_power(args: argparse.Namespace) -> int:
    lg = _league_from_args(args)
    rankings = lg.power_rankings()
    width = max((len(t.name) for t, _ in rankings), default=10)
    for i, (t, score) in enumerate(rankings, 1):
        print(f"{i:>2}  {t.name:<{width}}  score={score:>8.2f}  {t.record}")
    return 0


def _cmd_settings(args: argparse.Namespace) -> int:
    lg = _league_from_args(args)
    s = lg.settings()
    print(f"{s.name} ({s.season}) — {s.size}-team {s.scoring_type}")
    print(f"  playoff teams: {s.playoff_teams}")
    print(f"  regular-season periods: {s.regular_season_matchup_periods}")
    print("  roster:")
    for slot, count in s.roster_slots.items():
        print(f"    {slot}: {count}")
    if s.scoring:
        print("  scoring:")
        for item in s.scoring:
            print(f"    {item.stat_name}: {item.points:+.2f}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="espn-fb", description="ESPN Fantasy Baseball CLI")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--league", type=int, required=True, help="ESPN league id")
    common.add_argument("--year", type=int, required=True, help="Season year")
    common.add_argument("--espn-s2", default=None, help="espn_s2 cookie (private leagues)")
    common.add_argument("--swid", default=None, help="SWID cookie (private leagues)")

    sub = parser.add_subparsers(dest="command", required=True)

    p_standings = sub.add_parser("standings", parents=[common], help="Show current standings")
    p_standings.set_defaults(func=_cmd_standings)

    p_roster = sub.add_parser("roster", parents=[common], help="Show a team's roster")
    p_roster.add_argument("--team", type=int, required=True, help="Team id")
    p_roster.set_defaults(func=_cmd_roster)

    p_matchups = sub.add_parser("matchups", parents=[common], help="Show matchups for a week")
    p_matchups.add_argument("--week", type=int, required=True, help="Matchup period (week)")
    p_matchups.set_defaults(func=_cmd_matchups)

    p_fa = sub.add_parser("fa", parents=[common], help="List free agents")
    p_fa.add_argument("--size", type=int, default=25, help="How many players to return")
    p_fa.add_argument("--position", default=None, help="Filter by position (C, 1B, SP, RP, ...)")
    p_fa.set_defaults(func=_cmd_fa)

    p_draft = sub.add_parser("draft", parents=[common], help="Show the draft recap")
    p_draft.set_defaults(func=_cmd_draft)

    p_power = sub.add_parser("power", parents=[common], help="Show power rankings")
    p_power.set_defaults(func=_cmd_power)

    p_settings = sub.add_parser("settings", parents=[common], help="Show league settings")
    p_settings.set_defaults(func=_cmd_settings)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ESPNFantasyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
