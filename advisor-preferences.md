# Manager preferences for the AI advisor

The advisor reads this file on every run and must respect it. Edit freely —
or just tell Claude to update it.

**Last updated: 2026-08-23 (live session with the manager).**

## League mechanics (how transactions actually work here)

- **No direct-to-IL adds.** A player CANNOT be picked up and designated
  straight to an IL slot. Every add requires an open active-roster spot:
  with a full roster the sequence is drop someone → add the player → then
  move him to IL. An "IL stash" is NEVER free.
- **BE parking is legal.** A player can be moved to the bench overflow slot
  (scoring nothing) leaving an active slot empty — used to carry an extra
  pitcher and rotate arms, or to dodge a slumping pitcher's risky start.
- **3 adds per matchup.** Always state moves-remaining before recommending.
- **Verify pitcher roles in the ESPN app.** The "2 starts" tag on the add
  screen is authoritative; API probable-starter data has burned us
  (Quantrill was projected two starts while working from the bullpen).
  Never recommend a streaming add without a verified role.

## Manager philosophy (binding)

- **Season totals are a NON-FACTOR.** Judge on recent form (last 7 / last
  15) and future upside only. Never defend a hold with a season total.
- Prefers high-ceiling gambles ("the next Esmerlyn Valdez") for the last
  flexible spot: recent call-ups with pedigree + a fresh everyday job.
- Streaming: soft matchups beat arm pedigree; blowups score negative here.
- Cut the guy who JUST pitched / whose value was just banked ("squeezed
  lemon"), not the one about to play.

## Protected players (never recommend dropping)

Caminero, Suzuki, Tucker, Contreras, Moreno, Duran, Altuve, Valdez,
Messick, Kirby, Imanaga, Cade Smith.

- **Lottery tickets under a patience window (hold ≥2 weeks from add):**
  Kaelen Culpepper (added ~8/9), Spencer Jones, Zac Veen, Colt Keith,
  Rafael Flores Jr. Tripwire for Spencer Jones: Stanton activated AND
  Jones starts sitting — then he becomes droppable.
- **Kyle Teel (IL)** — keeper upside, hold through injury.

## Droppable pool (in order of preference)

1. **Cal Quantrill** — long reliever, first out for any verified starter.
2. **Jared Jones** — negative recent stretches; bench his risky starts,
   drop if the slide continues. (Manager likes him — flag before proposing.)
3. **Willi Castro** — fine, replaceable for clear upgrades.
4. **Roki Sasaki** — only for an elite SP upgrade (Skubal squeezed the
   LAD rotation; watch his spot).
5. **Ryan Jeffers** — only if a hotter C/1B bat (e.g. Flores) forces it.
6. IL players to free an IL slot only: Abel first, O'Hearn (out ~mid-Sept)
   last resort. Lawlar is already slated to be dropped.

## Standing context (as of 8/23)

- Pending/planned adds: Veen ⟵ Nootbaar, Buehler ⟵ Quantrill,
  Flores Jr. ⟵ Lawlar. Do not re-litigate; grade and build on them.
- Eovaldi on 15-day IL; O'Hearn (quad, 6–8 wks) on IL.
- Kade Anderson was claimed by another team (id 12) on 8/22 — gone.
