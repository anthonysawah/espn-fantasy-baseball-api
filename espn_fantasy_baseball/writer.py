"""Write operations against the ESPN Fantasy Baseball API.

Read endpoints live on ``lm-api-reads``; writes go to
``lm-api-writes.fantasy.espn.com``.  All writes require a valid
``espn_s2`` + ``SWID`` cookie pair.

Supported operations
--------------------

* **Set lineup** — move players between lineup slots for a given scoring period.
* **Add / drop (free agent / waiver)** — pick up a free agent or waiver
  claim, optionally dropping another player in the same transaction.
* **Move to / off IL** — convenience wrappers that shift a player into or
  out of the IL slot.
* **Apply lineup plan** — take the output of :func:`optimize_lineup` and
  submit every non-identity move in one batch.
* **Propose trade** — send a multi-leg trade offer to another team.
* **Respond to trade** — accept or reject an inbound proposal.

The write body shapes below are based on what the espn.com UI sends.
ESPN changes them occasionally; if a method breaks, capture the payload
from your browser's Network tab and compare.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .client import ESPNClient
from .constants import FANTASY_WRITE_BASE
from .exceptions import AuthenticationError
from .optimizer import BENCH_SLOTS, IL_SLOT, LineupMove, LineupPlan

# Reverse-map of LINEUP_SLOT_MAP for the slots users are likely to target.
# We keep this explicit so that ambiguous abbreviations (e.g. "OF" which
# matches lineup slot 5) land on the right id.
_SLOT_NAME_TO_ID: dict[str, int] = {
    "C": 0, "1B": 1, "2B": 2, "3B": 3, "SS": 4,
    "OF": 5, "2B/SS": 6, "1B/3B": 7,
    "LF": 8, "CF": 9, "RF": 10,
    "DH": 11, "UTIL": 12,
    "P": 13, "SP": 14, "RP": 15,
    "BE": 16, "Bench": 16,
    "IL": 17,
}


@dataclass
class WriteResult:
    """The server's response to a write operation."""

    ok: bool
    status_code: int
    payload: Any
    url: str

    def raise_for_status(self) -> None:
        if not self.ok:
            raise AuthenticationError(f"ESPN rejected write ({self.status_code}): {self.payload!r}")


class LeagueWriter:
    """Authenticated write operations for a single team in a league.

    Do not construct directly; use :meth:`League.writer`.
    """

    def __init__(self, client: ESPNClient, team_id: int):
        if not (client.espn_s2 and client.swid):
            raise AuthenticationError(
                "Write operations require both espn_s2 and swid cookies."
            )
        self._client = client
        self.team_id = int(team_id)

    # ------------------------------------------------------------------
    # Internal POST helper
    # ------------------------------------------------------------------

    def _write_url(self) -> str:
        c = self._client
        return (
            f"{FANTASY_WRITE_BASE}/seasons/{c.year}/segments/0/leagues/{c.league_id}"
            f"/transactions/"
        )

    def _post(self, body: Mapping[str, Any]) -> WriteResult:
        """Issue a POST to the transactions endpoint."""
        url = self._write_url()
        response = self._client.session.request(
            "POST",
            url,
            json=dict(body),
            headers={"Content-Type": "application/json"},
            timeout=self._client.timeout,
        )
        try:
            payload = response.json()
        except ValueError:
            payload = response.text
        return WriteResult(
            ok=200 <= response.status_code < 300,
            status_code=response.status_code,
            payload=payload,
            url=url,
        )

    # ------------------------------------------------------------------
    # Lineup
    # ------------------------------------------------------------------

    def set_lineup(
        self,
        moves: Iterable[Mapping[str, Any]],
        *,
        scoring_period: int,
    ) -> WriteResult:
        """Execute a batch of lineup slot changes.

        ``moves`` is an iterable of dicts with keys:

        * ``player_id`` — the ESPN player id
        * ``from_slot`` — current lineup slot (name or id)
        * ``to_slot``   — target lineup slot (name or id)
        """
        items: list[dict[str, Any]] = []
        for m in moves:
            items.append(
                {
                    "playerId": int(m["player_id"]),
                    "type": "LINEUP",
                    "fromLineupSlotId": _slot_id(m["from_slot"]),
                    "toLineupSlotId": _slot_id(m["to_slot"]),
                }
            )
        body = {
            "isLeagueManager": False,
            "teamId": self.team_id,
            "type": "LINEUP",
            "scoringPeriodId": int(scoring_period),
            "items": items,
        }
        return self._post(body)

    def apply_plan(self, plan: LineupPlan, *, scoring_period: int) -> WriteResult:
        """Apply every non-identity move from :func:`optimize_lineup`."""
        moves = [
            {
                "player_id": m.player.id,
                "from_slot": m.from_slot or "BE",
                "to_slot": m.to_slot,
            }
            for m in plan.changes()
        ]
        if not moves:
            return WriteResult(ok=True, status_code=204, payload={"noop": True}, url="")
        return self.set_lineup(moves, scoring_period=scoring_period)

    # ------------------------------------------------------------------
    # Add / drop / IL
    # ------------------------------------------------------------------

    def add_player(
        self,
        player_id: int,
        *,
        drop_player_id: int | None = None,
        bid_amount: int = 0,
        scoring_period: int,
        via_waiver: bool = False,
    ) -> WriteResult:
        """Claim a free-agent or waiver player, optionally dropping another.

        For auction / FAAB leagues, pass ``bid_amount``.  For waiver claims
        use ``via_waiver=True`` to queue rather than execute immediately.
        """
        items = [{"playerId": int(player_id), "type": "ADD"}]
        if drop_player_id is not None:
            items.append({"playerId": int(drop_player_id), "type": "DROP"})
        body = {
            "bidAmount": int(bid_amount),
            "executionType": "QUEUE" if via_waiver else "EXECUTE",
            "isActingAsTeamOwner": False,
            "isLeagueManager": False,
            "teamId": self.team_id,
            "scoringPeriodId": int(scoring_period),
            "type": "WAIVER" if via_waiver else "FREEAGENT",
            "items": items,
        }
        return self._post(body)

    def drop_player(self, player_id: int, *, scoring_period: int) -> WriteResult:
        """Drop a player without adding a replacement."""
        body = {
            "isLeagueManager": False,
            "teamId": self.team_id,
            "scoringPeriodId": int(scoring_period),
            "type": "FREEAGENT",
            "executionType": "EXECUTE",
            "items": [{"playerId": int(player_id), "type": "DROP"}],
        }
        return self._post(body)

    def move_to_il(
        self,
        player_id: int,
        *,
        from_slot: str | int = "BE",
        scoring_period: int,
    ) -> WriteResult:
        """Shift an injured player from their current slot onto the IL."""
        return self.set_lineup(
            [{"player_id": player_id, "from_slot": from_slot, "to_slot": IL_SLOT}],
            scoring_period=scoring_period,
        )

    def move_off_il(
        self,
        player_id: int,
        *,
        to_slot: str | int = "BE",
        scoring_period: int,
    ) -> WriteResult:
        """Pull a player off the IL, landing them on the bench by default."""
        return self.set_lineup(
            [{"player_id": player_id, "from_slot": IL_SLOT, "to_slot": to_slot}],
            scoring_period=scoring_period,
        )

    # ------------------------------------------------------------------
    # Trades
    # ------------------------------------------------------------------

    def propose_trade(
        self,
        *,
        to_team_id: int,
        offering: Iterable[int],
        requesting: Iterable[int],
        expiration_days: int = 2,
    ) -> WriteResult:
        """Send a multi-leg trade proposal.

        ``offering`` is the list of your players you're giving up;
        ``requesting`` is the list from the other team that you want.
        """
        items: list[dict[str, Any]] = []
        for pid in offering:
            items.append(
                {
                    "playerId": int(pid),
                    "type": "TRADE_PROPOSAL",
                    "fromTeamId": self.team_id,
                    "toTeamId": int(to_team_id),
                }
            )
        for pid in requesting:
            items.append(
                {
                    "playerId": int(pid),
                    "type": "TRADE_PROPOSAL",
                    "fromTeamId": int(to_team_id),
                    "toTeamId": self.team_id,
                }
            )
        body = {
            "isLeagueManager": False,
            "teamId": self.team_id,
            "type": "TRADE_PROPOSAL",
            "tradeExpirationHours": int(expiration_days) * 24,
            "items": items,
        }
        return self._post(body)

    def respond_to_trade(self, trade_id: int, *, accept: bool) -> WriteResult:
        """Accept or reject an incoming trade proposal."""
        body = {
            "isLeagueManager": False,
            "teamId": self.team_id,
            "type": "TRADE_ACCEPT" if accept else "TRADE_DECLINE",
            "tradeId": int(trade_id),
        }
        return self._post(body)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _slot_id(slot: str | int) -> int:
    if isinstance(slot, int):
        return slot
    if slot in _SLOT_NAME_TO_ID:
        return _SLOT_NAME_TO_ID[slot]
    raise ValueError(f"Unknown lineup slot: {slot!r}")
