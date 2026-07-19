# Manager preferences for the AI advisor

The advisor reads this file on every run and must respect it. Edit freely —
or just tell Claude to update it.

## League mechanics (how transactions actually work here)

- **No direct-to-IL adds.** A player CANNOT be picked up and designated
  straight to an IL slot. Every add requires an open active-roster spot:
  with a full roster the sequence is drop someone → add the player → then
  move him to IL. Therefore an "IL stash" is NEVER free — it costs a drop
  from the droppable pool like any other add, plus the added player
  contributes nothing until activated.

- **Matchup structure varies:** some matchup periods span TWO WEEKS (e.g.,
  around the All-Star break — matchup 15 in 2026 runs through ~7/26). Never
  assume a matchup ends Sunday; check the schedule window first.
- **Acquisition limit is per-matchup** at a rate of 3 per 7 days (= 5 in a
  two-week matchup; stored as matchupAcquisitionLimit 0.42857/day). BEFORE
  recommending any add, ALWAYS check `transactionCounter.matchupAcquisitionTotals`
  for the current period — for OUR team (moves remaining) AND the opponent
  (their counter-move capacity). State both in every report.

## Droppable pool (hard boundary)

The manager considers ONLY these active-roster players potentially
droppable: **Griffin Jax**, **Willi Castro**, **Ezequiel Duran**. Do not
propose dropping anyone else on the active roster, period.

- Duran's recent hot stretch may take him off this list — check his
  computed trend before proposing him, and flag it if he's heating.
- IL-slot players (currently Mick Abel, Jordan Lawlar) are a separate
  category: they may be proposed as drops only to free an IL slot, with
  their verified return timeline weighed first.
- If an add has no acceptable drop within this pool, recommend skipping
  the add.

## Protected players (never recommend dropping)

- **Kyle Teel (C, CHW)** — young catcher with keeper upside, now in an
  everyday role and hitting in most of his recent starts. Holding through
  the growing pains; do not propose him as a drop.

## Player notes

- **Ryan Jeffers (C, MIN)** — do not propose dropping him. Second-most
  productive catcher on the roster this season (361 pts), projection tied
  for best among the backups, and trending up (16 pts in the last 7 days).
  A slow 30-day window is not a reason to cut him.

- **Kody Clemens (MIN)** — the manager rates his hot bat (86 pts over the
  last 30 days, 5 HR in 8 games in early July) above his modest
  rest-of-season projection. Treat him as effectively protected while the
  bat stays hot; he is NOT in the droppable pool.

## Strategy

- This is a 1-keeper league: weigh keeper value (young players, breakouts
  on cheap acquisition cost) in every hold/drop call, not just this
  season's points.
- Deep 14-team league: assume any useful player dropped is gone for good.
- When judging form, weight the most recent 7 days over the 30-day window —
  a player whose last-7 outpaces his last-30 is heating up, not cold. Never
  call a player "cold" off an old window when the recent trend is up.
- No forced moves: if an add has no clearly weaker drop candidate, recommend
  skipping the add entirely rather than manufacturing a drop.
