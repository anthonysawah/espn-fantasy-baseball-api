"""AI-powered roster advisor built on the Claude API.

Gathers a snapshot of your league — your roster (with hot/cold splits and
injury statuses), the free-agent pool, standings, your current matchup and
recent league transactions — and asks Claude for concrete, prioritized
recommendations: who to pick up, who to drop, who to stream, and what
lineup or trade moves to consider.

Requires the optional ``anthropic`` dependency::

    pip install "espn-fantasy-baseball-api[ai]"

Typical usage::

    from espn_fantasy_baseball import League
    from espn_fantasy_baseball.advisor import Advisor

    lg = League(league_id=123456, year=2025, espn_s2="...", swid="{...}")
    advisor = Advisor(lg, team_id=1)          # reads ANTHROPIC_API_KEY
    report = advisor.advise()
    print(report.markdown)
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .exceptions import ESPNFantasyError
from .resources import Player, Team

if TYPE_CHECKING:
    from .league import League

DEFAULT_MODEL = "claude-opus-4-8"

#: Positions scanned individually when building the free-agent section.
DEFAULT_FA_POSITIONS = ("SP", "RP", "C", "OF", "SS")

SYSTEM_PROMPT = """\
You are an expert fantasy baseball analyst advising one specific team in an \
ESPN fantasy baseball league. You are given a snapshot of the league: the \
scoring settings, standings, the manager's full roster (with recent \
performance splits and injury statuses), the current matchup, the top \
available free agents, and recent league transactions.

Produce a concise, actionable report in Markdown with these sections:

## TL;DR
Three to five bullet points with your highest-priority moves.

## Pickups
The best available free agents for THIS roster, ranked. For each: who to \
add, who to drop to make room (from this roster only), and a one-to-two \
sentence rationale grounded in the numbers provided (recent performance, \
ownership trend, positional need, injuries).

## Drops / Watch List
Rostered players who are droppable or trending the wrong way, and why.

## Lineup & Injury Notes
Injured or inactive players who need an IL move or bench, and any starters \
being outscored by bench players.

## Matchup Strategy
One short paragraph: how to approach the current matchup given the score \
and rosters (e.g. stream starts, punt a category, play it safe).

Rules:
- Only recommend adding players listed in the FREE AGENTS section, and only
  recommend dropping players on the manager's roster.
- Ground every claim in the data provided; do not invent stats. If the data
  is insufficient for a judgment, say so briefly rather than guessing.
- Respect the league's scoring type when weighing players.
- Be decisive: rank options and commit to recommendations.\
"""


class AdvisorError(ESPNFantasyError):
    """Raised when the AI advisor cannot produce a report."""


@dataclass
class AdviceReport:
    """The advisor's output: a Markdown report plus the context that produced it."""

    markdown: str
    model: str
    context: str
    usage: dict[str, Any] = field(default_factory=dict)


class Advisor:
    """Builds league context and asks Claude for roster recommendations.

    Parameters
    ----------
    league:
        A :class:`~espn_fantasy_baseball.League` (auth cookies recommended so
        rosters are visible in private leagues).
    team_id:
        The ESPN team id of *your* team.
    model:
        Claude model id.  Defaults to ``claude-opus-4-8``.
    api_key:
        Anthropic API key.  Defaults to the ``ANTHROPIC_API_KEY`` env var.
    anthropic_client:
        Pre-built ``anthropic.Anthropic`` client (mainly for testing).
    fa_size:
        How many free agents to scan per list (overall + per position).
    fa_positions:
        Positions to scan individually in the free-agent pool.
    """

    def __init__(
        self,
        league: League,
        team_id: int,
        *,
        model: str = DEFAULT_MODEL,
        api_key: str | None = None,
        anthropic_client: Any = None,
        fa_size: int = 20,
        fa_positions: Iterable[str] = DEFAULT_FA_POSITIONS,
    ) -> None:
        self.league = league
        self.team_id = team_id
        self.model = model
        self.fa_size = fa_size
        self.fa_positions = tuple(fa_positions)
        if anthropic_client is not None:
            self._client = anthropic_client
        else:
            self._client = _build_anthropic_client(api_key)

    # ------------------------------------------------------------------
    # Context building (pure ESPN data, no AI)
    # ------------------------------------------------------------------

    def build_context(self) -> str:
        """Assemble the league snapshot fed to Claude, as plain Markdown."""
        lg = self.league
        sections = [
            _settings_section(lg),
            _standings_section(lg, self.team_id),
            _roster_section(lg.team(self.team_id)),
            _matchup_section(lg, self.team_id),
            _free_agents_section(lg, size=self.fa_size, positions=self.fa_positions),
            _activity_section(lg),
        ]
        return "\n\n".join(s for s in sections if s)

    # ------------------------------------------------------------------
    # AI call
    # ------------------------------------------------------------------

    def advise(self, focus: str | None = None) -> AdviceReport:
        """Generate an :class:`AdviceReport` for this team.

        ``focus`` is an optional extra question to emphasise, e.g.
        ``"I need saves — who should I target?"``.
        """
        context = self.build_context()
        user_prompt = f"Here is the current league snapshot:\n\n{context}"
        if focus:
            user_prompt += f"\n\nIn addition to the standard report, address this: {focus}"

        with self._client.messages.stream(
            model=self.model,
            max_tokens=16000,
            thinking={"type": "adaptive"},
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        ) as stream:
            message = stream.get_final_message()

        if getattr(message, "stop_reason", None) == "refusal":
            raise AdvisorError("The model declined to produce a report for this request.")

        markdown = "".join(
            block.text for block in message.content if getattr(block, "type", None) == "text"
        )
        if not markdown.strip():
            raise AdvisorError("The model returned an empty report.")

        usage = getattr(message, "usage", None)
        usage_dict: dict[str, Any] = {}
        if usage is not None:
            for key in ("input_tokens", "output_tokens"):
                value = getattr(usage, key, None)
                if value is not None:
                    usage_dict[key] = value
        return AdviceReport(markdown=markdown, model=self.model, context=context, usage=usage_dict)


# ---------------------------------------------------------------------------
# Anthropic client construction
# ---------------------------------------------------------------------------


def _build_anthropic_client(api_key: str | None) -> Any:
    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover - exercised via error message test
        raise AdvisorError(
            "The AI advisor requires the 'anthropic' package. "
            'Install it with: pip install "espn-fantasy-baseball-api[ai]"'
        ) from exc
    if api_key is not None:
        return anthropic.Anthropic(api_key=api_key)
    return anthropic.Anthropic()


# ---------------------------------------------------------------------------
# Context sections
# ---------------------------------------------------------------------------


def _settings_section(lg: League) -> str:
    s = lg.settings()
    lines = [
        "# LEAGUE",
        f"{s.name} — season {s.season}, {s.size} teams, scoring: {s.scoring_type}",
        "Roster slots: " + ", ".join(f"{slot}×{n}" for slot, n in s.roster_slots.items()),
    ]
    if s.acquisition_budget:
        lines.append(f"FAAB budget: {s.acquisition_budget}")
    if s.scoring:
        rules = ", ".join(f"{i.stat_name} {i.points:+g}" for i in s.scoring)
        lines.append(f"Scoring rules: {rules}")
    return "\n".join(lines)


def _standings_section(lg: League, team_id: int) -> str:
    lines = ["# STANDINGS"]
    for rank, t in enumerate(lg.standings(), 1):
        marker = "  <-- YOUR TEAM" if t.id == team_id else ""
        lines.append(
            f"{rank}. {t.name} ({t.record})  PF={t.points_for:.1f} PA={t.points_against:.1f}{marker}"
        )
    return "\n".join(lines)


def _roster_section(team: Team) -> str:
    lines = [
        "# YOUR ROSTER",
        f"{team.name} ({team.record}) — moves made: {team.moves}, FAAB spent: {team.acquisition_budget_spent}",
    ]
    for label, players in (
        ("Starters", team.starters()),
        ("Bench", team.bench()),
        ("IL", team.injured()),
    ):
        if not players:
            continue
        lines.append(f"## {label}")
        lines.extend(_player_line(p, slot=True) for p in players)
    return "\n".join(lines)


def _matchup_section(lg: League, team_id: int) -> str:
    try:
        matchups = lg.scoreboard()
    except ESPNFantasyError:
        return ""
    for m in matchups:
        if team_id not in (m.home_team_id, m.away_team_id):
            continue
        we_are_home = m.home_team_id == team_id
        opp_id = m.away_team_id if we_are_home else m.home_team_id
        our_score = m.home_score if we_are_home else m.away_score
        opp_score = m.away_score if we_are_home else m.home_score
        opp_name = f"team #{opp_id}"
        if opp_id is not None:
            with contextlib.suppress(KeyError):
                opp_name = lg.team(opp_id).name
        return (
            "# CURRENT MATCHUP\n"
            f"Week {m.matchup_period}: you have {our_score:.1f} points vs "
            f"{opp_name} with {opp_score:.1f} points."
        )
    return ""


def _free_agents_section(lg: League, *, size: int, positions: tuple[str, ...]) -> str:
    lines = ["# FREE AGENTS"]

    def _add_list(title: str, players: list[Player]) -> None:
        if not players:
            return
        lines.append(f"## {title}")
        lines.extend(_player_line(p) for p in players)

    _add_list("Hottest (last 7 days)", lg.free_agents(size=size, sort_by="last7_points"))
    _add_list("Most owned", lg.free_agents(size=size, sort_by="percent_owned"))
    for pos in positions:
        _add_list(f"Top {pos}", lg.free_agents(size=min(size, 10), position=pos))
    return "\n".join(lines)


def _activity_section(lg: League) -> str:
    try:
        events = lg.recent_activity(size=15)
    except ESPNFantasyError:
        return ""
    if not events:
        return ""
    lines = ["# RECENT LEAGUE TRANSACTIONS"]
    for e in events:
        when = e.date.strftime("%Y-%m-%d") if e.date else "?"
        parts = []
        for a in e.actions:
            label = a.player_name or f"player #{a.player_id}"
            bid = f" (bid {a.bid_amount})" if a.bid_amount else ""
            parts.append(f"{a.type} {label} by team {a.team_id}{bid}")
        lines.append(f"- {when} {e.type}: " + "; ".join(parts))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Player formatting
# ---------------------------------------------------------------------------


def _split_total(player: Player, split: str) -> float | None:
    for s in player.stats:
        if s.split == split and s.source == "real":
            return s.applied_total
    return None


def _player_line(p: Player, *, slot: bool = False) -> str:
    positions = "/".join(p.eligible_positions) or "?"
    bits = [f"- {p.name} ({p.pro_team}, {positions})"]
    if slot and p.lineup_slot:
        bits.append(f"slot={p.lineup_slot}")
    season = _split_total(p, "season")
    if season is not None:
        bits.append(f"season_pts={season:.1f}")
    for split, label in (("last_7", "last7_pts"), ("last_15", "last15_pts")):
        total = _split_total(p, split)
        if total is not None:
            bits.append(f"{label}={total:.1f}")
    bits.append(f"owned={p.percent_owned:.1f}%")
    if p.injury_status and p.injury_status not in {"ACTIVE", "Active"}:
        bits.append(f"INJURY={p.injury_status}")
    return "  ".join(bits)
