# Authenticating against private ESPN leagues

ESPN's Fantasy API requires two cookies for private leagues:

- **`espn_s2`** — a long opaque auth token (~300+ characters).
- **`SWID`** — your user id, a UUID wrapped in braces (e.g. `{ABCD-1234-...}`).

## Finding them in your browser

1. Log in to [fantasy.espn.com](https://fantasy.espn.com) and open your
   league.
2. Open your browser's DevTools:
   - **Chrome / Edge**: F12 → **Application** → **Storage → Cookies →
     `https://fantasy.espn.com`**
   - **Firefox**: F12 → **Storage** → **Cookies → `https://fantasy.espn.com`**
   - **Safari**: enable "Develop" menu, then **Web Inspector → Storage →
     Cookies**
3. Copy the values of the `espn_s2` and `SWID` cookies.

## Using them

```python
from espn_fantasy_baseball import League

lg = League(
    league_id=123456,
    year=2024,
    espn_s2="AECz...",
    swid="{12345678-ABCD-...}",   # braces are optional — we add them
)
```

Or via environment variables (picked up automatically by the CLI):

```bash
export ESPN_S2="AECz..."
export SWID="{12345678-ABCD-...}"
espn-fb standings --league 123456 --year 2024
```

## Notes

- The `espn_s2` cookie **expires** (typically within a year). If your
  previously-working script starts raising `PrivateLeagueError`, re-copy
  the cookie from your browser.
- **Treat `espn_s2` like a password.** Anyone who has it can act as you on
  espn.com. Don't commit it to source control.
- You do not need cookies for **public leagues** — just pass `league_id`
  and `year`.
