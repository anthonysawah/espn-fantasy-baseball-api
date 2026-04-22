# FAQ

## General

### Is this library affiliated with ESPN?

No. ESPN's Fantasy API is undocumented; this is a community-maintained
reverse-engineered client. ESPN can change or break it at any time.

### What's my `league_id`?

It's the big number in the URL of your league's home page:

```
https://fantasy.espn.com/baseball/league?leagueId=123456&...
                                                  ^^^^^^
```

### What seasons are supported?

Anything ESPN still serves — usually the current season and a handful
of prior ones through the "current" endpoint, and older ones via the
league-history endpoint. We transparently route between them based on
the year you pass.

Very old seasons (pre-2018 or so) may 400 with `InvalidSeasonError`.

---

## Authentication

### Do I need cookies for my league?

Only for **private** leagues (the default for most leagues). Public
leagues work with just `league_id` and `year`.

### My script worked yesterday and now gets `PrivateLeagueError`.

Your `espn_s2` cookie expired. They generally last a few months. Log
in to espn.com in your browser, copy the new cookie, update your
environment.

### Do I need to wrap `SWID` in braces?

No — we add them for you if they're missing. Both `{abc-123}` and
`abc-123` work.

### Can I use this from GitHub Actions?

Yes, put `ESPN_S2` and `SWID` in the repo's **encrypted secrets** and
read them via `os.environ`. Never check them into source control.

---

## Errors

### `LeagueNotFoundError`

Either the `league_id` is wrong, or the season hasn't started yet and
ESPN hasn't created the endpoint for it.

### `InvalidSeasonError`

ESPN rejected the season id — usually because it's in the future, or
too old for the historical endpoint.

### `PrivateLeagueError`

Missing or expired cookies. See [AUTHENTICATION.md](./AUTHENTICATION.md).

### `ESPNAPIError` with a 5xx status

Usually a transient ESPN hiccup. We already retry up to 3 times with
exponential backoff. If you see persistent 5xxs, try again later or
bump `max_retries=`.

---

## Data

### Stats come back as `{"5": 30}` — why?

You're looking at `player.raw`. The decoded `player.stats` (or
`player.season_stats()`) gives you `{"HR": 30}`.

### How do I tell a pitcher from a batter?

`player.is_pitcher()` / `player.is_batter()`.

### Where are projections?

On `player.stats` — each `PlayerStats` entry has `source="real"` or
`"projected"`. Use `player.season_stats(projected=True)`.

### Why is `standings_rank` sometimes `None`?

Early in the season ESPN leaves some ranking fields unpopulated. The
`standings()` method sorts by computed record regardless.

### Why do I see duplicate matchups in `schedule()`?

ESPN represents each matchup once, but if you're in a league with
playoffs the same two teams can appear in multiple later periods.

---

## Performance / limits

### Am I going to get rate-limited?

ESPN doesn't publish limits. In practice we haven't seen issues for
normal personal use. The client retries on 429 with backoff, and
`League` caches within the process so you don't re-hit ESPN on
repeated reads.

### Can I parallelize calls?

Yes — pass your own pre-warmed `requests.Session` (or an
`httpx`/`asyncio` compatible wrapper) and call multiple
`League` instances concurrently. The client itself is thread-safe as
long as the underlying session is.

### The first call is slow.

It pays for the TLS handshake. Reuse the same `League` instance (or a
shared `requests.Session`) and subsequent calls are much faster.

---

## Scope

### Can I change my lineup / add / drop / trade from this library?

**Yes — as of v0.2.** See the [Writing section in API.md](./API.md) and
the cookbook for `lg.lineup_optimizer(...)`, `lg.add_player(...)`,
`lg.drop_player(...)`, `lg.move_to_il(...)`, and
`lg.propose_trade(...)`. Write operations require valid auth cookies.

### Does this work for ESPN Fantasy Football / Basketball / Hockey?

No — this library is baseball-only. Other sports have very similar
endpoints (`ffl`, `fba`, `fhl` instead of `flb`) but different
stat/slot ids; a future sibling package could share most of the
scaffolding.

### Will you add async support?

Maybe. Open an issue if you need it — it would be a thin wrapper
around `httpx.AsyncClient` and wouldn't change the public API much.
