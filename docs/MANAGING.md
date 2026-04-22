# Managing your team

Everything under this heading requires **authentication**. Construct
your `League` with valid `espn_s2` + `SWID` cookies, then get a
`LeagueWriter` scoped to your team:

```python
from espn_fantasy_baseball import League

lg = League(league_id=123456, year=2024, espn_s2="...", swid="{...}")
w = lg.writer(team_id=1)   # your team
```

If the cookies are missing the writer raises `AuthenticationError`
before sending anything over the wire.

---

## Scoring periods

Every write takes a `scoring_period=` argument. ESPN thinks of the
season as a sequence of numbered scoring periods (daily in baseball).
Passing the wrong period usually silently does nothing, or applies
your move on the wrong day — so look it up:

```python
status = lg.client.get(views=["mStatus"])
current_period = status["status"]["currentMatchupPeriod"]
```

Or, easier, read `lg.schedule()[-1].matchup_period`.

---

## Setting lineups

### Low-level: tell ESPN exactly what to do

```python
w.set_lineup(
    [
        {"player_id": 41234, "from_slot": "BE", "to_slot": "2B"},
        {"player_id": 39928, "from_slot": "2B", "to_slot": "BE"},
    ],
    scoring_period=115,
)
```

`from_slot` / `to_slot` accept either the string abbreviation (`"C"`,
`"OF"`, `"BE"`, `"IL"`, `"SP"`, …) or the raw ESPN slot id.

### High-level: let the optimizer decide

```python
plan = lg.optimize_lineup(team_id=1)
print(plan.summary())

# Ship only the *changes* — the optimizer already knows not to churn
# slots that are already optimal.
w.apply_plan(plan, scoring_period=115)
```

By default the optimizer scores each player by their season applied
total (or a projection if ESPN attached one). Supply your own:

```python
my_projections = {41234: 15.1, 39928: 9.4, 88888: 22.0}
plan = lg.optimize_lineup(team_id=1, projections=my_projections)
```

The optimizer:

- Respects every player's eligible positions.
- Packs starter slots greedily from scarcest position first (so a SS-only
  player doesn't lose their slot to a more valuable UTIL-eligible bat).
- Routes anyone with an IL-flavored `injury_status` to the IL slot if
  one is open.
- Pushes everybody else to the bench.

If demand exceeds your roster (rare), `plan.unfilled_slots` lists which
slots couldn't be filled.

---

## Adding and dropping

### Free-agent pickup

```python
w.add_player(
    player_id=41234,
    drop_player_id=39928,   # optional; omit to just add if you have a spot
    bid_amount=0,           # FAAB bid; 0 for free leagues
    scoring_period=115,
)
```

### Waiver claim (queued, processes on the league's waiver schedule)

```python
w.add_player(
    player_id=41234,
    drop_player_id=39928,
    bid_amount=7,
    scoring_period=115,
    via_waiver=True,        # <-- queues rather than executes
)
```

### Just drop someone

```python
w.drop_player(player_id=39928, scoring_period=115)
```

---

## IL management

The IL is just another lineup slot, so IL moves go through the same
machinery as lineup changes — we expose convenience wrappers so you
don't have to remember slot ids:

```python
# Player got hurt, shelve them
w.move_to_il(player_id=39928, from_slot="2B", scoring_period=115)

# They're back — pull them off IL to the bench, then optimize
w.move_off_il(player_id=39928, to_slot="BE", scoring_period=115)
plan = lg.optimize_lineup(team_id=1)
w.apply_plan(plan, scoring_period=115)
```

ESPN rejects IL moves for players who aren't flagged injured by their
`injuryStatus`. Check `player.injury_status` before trying.

---

## Trades

### Propose a trade

```python
w.propose_trade(
    to_team_id=2,
    offering=[41234, 39928],   # your players you're giving up
    requesting=[88888],        # their players you want
    expiration_days=2,         # how long before the offer auto-expires
)
```

ESPN handles draft-pick trades in the write payload differently by
sport; this library covers the standard player-for-player case. For
pick-for-player or pick-for-pick deals you'll want to build the body
manually via `writer._post(...)` (happy to accept a PR).

### Accept or reject an incoming proposal

```python
w.respond_to_trade(trade_id=77, accept=True)
w.respond_to_trade(trade_id=78, accept=False)
```

You can list pending proposals via the activity feed
(`lg.recent_activity()`).

---

## Inspecting what ESPN said

Every write returns a `WriteResult`:

```python
result = w.add_player(41234, scoring_period=115)
if not result.ok:
    print("ESPN said no:", result.status_code, result.payload)
```

`result.raise_for_status()` raises `AuthenticationError` on a non-2xx
response.

---

## CLI

Most of the above is available from the command line (set
`ESPN_S2` / `SWID` in the environment):

```bash
# Compute and apply the best lineup
espn-fb optimize --league 123456 --year 2024 --team 1 --apply --period 115

# Add / drop / IL / trade
espn-fb add   --league 123456 --year 2024 --team 1 --player 41234 --drop 39928 --bid 7 --period 115
espn-fb drop  --league 123456 --year 2024 --team 1 --player 10001 --period 115
espn-fb il-on --league 123456 --year 2024 --team 1 --player 39928 --from-slot 2B --period 115
espn-fb trade --league 123456 --year 2024 --team 1 --to-team 2 \
              --offering 41234 39928 --requesting 88888

# Analytics
espn-fb insights --league 123456 --year 2024 --week 12
```

---

## Caveats

- ESPN's write API sometimes returns **200 OK with an error inside the
  body** for borderline illegal moves (e.g. a lineup change after
  lineup lock). `result.ok` reflects only the HTTP status; inspect
  `result.payload` for application-level failures.
- Lineup lock times are per-scoring-period and per-slot (starters lock
  at first pitch). Submit early.
- The write endpoint uses a different host (`lm-api-writes...`) than
  reads. If you're routing through a corporate proxy, allow both.
