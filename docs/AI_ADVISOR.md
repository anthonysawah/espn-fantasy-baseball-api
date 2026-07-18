# AI Advisor

The AI advisor connects your ESPN league to Claude and produces a
prioritized, actionable report for **your** team:

- **Pickups** — the best available free agents for your roster, who to drop
  for them, and why (recent performance, ownership trends, positional need).
- **Drops / watch list** — rostered players trending the wrong way.
- **Lineup & injury notes** — IL moves you're missing, bench players
  outscoring starters.
- **Matchup strategy** — how to play the current week given the score.

It works by building a text snapshot of your league (settings + scoring,
standings, your full roster with last-7/last-15 splits and injury statuses,
the current matchup, the hottest and most-owned free agents overall and by
position, and recent league transactions) and asking Claude to analyze it.

## Setup

1. Install the AI extra:

   ```bash
   pip install "espn-fantasy-baseball-api[ai]"
   ```

2. Get a Claude API key from [console.anthropic.com](https://console.anthropic.com)
   and export it:

   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   ```

3. For private leagues, export your ESPN cookies as usual (see
   [AUTHENTICATION.md](./AUTHENTICATION.md)):

   ```bash
   export ESPN_S2="..."
   export SWID="{...}"
   ```

## CLI

```bash
espn-fb advise --league 123456 --year 2025 --team 1
```

Options:

| Flag | Purpose |
| --- | --- |
| `--team ID` | Your team id (required). |
| `--focus "..."` | Extra question to emphasise, e.g. `"I need saves"`. |
| `--fa-size N` | Free agents to scan per list (default 20). |
| `--model ID` | Claude model (default `claude-opus-4-8`). |
| `--output FILE` | Write the Markdown report to a file instead of stdout. |

Don't know your team id? Run `espn-fb standings` and count, or check the
`teamId` query parameter in the URL of your team page on fantasy.espn.com.

## Python API

```python
from espn_fantasy_baseball import League, Advisor

lg = League(league_id=123456, year=2025, espn_s2="...", swid="{...}")
advisor = Advisor(lg, team_id=1)

report = advisor.advise(focus="Should I stream starters this week?")
print(report.markdown)          # the recommendation report
print(report.context)           # the raw league snapshot sent to Claude
print(report.usage)             # token usage
```

`Advisor` accepts `model=`, `fa_size=`, `fa_positions=`, `api_key=` and (for
testing) `anthropic_client=`. `build_context()` returns the snapshot without
calling the AI, which is handy for debugging what the model sees.

## Scheduled daily reports (GitHub Actions)

The repo ships a workflow, [`.github/workflows/ai-advisor.yml`](../.github/workflows/ai-advisor.yml),
that runs every morning at 7:00 AM ET and posts the report as a **GitHub
issue** in your fork/repo — so you get a notification and a browsable
archive of every report.

To enable it, add these repository secrets
(*Settings → Secrets and variables → Actions*):

| Secret | Value |
| --- | --- |
| `LEAGUE_ID` | Your ESPN league id. |
| `TEAM_ID` | Your team id. |
| `ESPN_S2` | The `espn_s2` cookie (private leagues). |
| `SWID` | The `SWID` cookie (private leagues). |
| `ANTHROPIC_API_KEY` | Your Claude API key. |
| `SEASON` | *(optional)* Season year; defaults to the current year. |

You can also trigger it on demand from the *Actions* tab
(*AI Advisor → Run workflow*), optionally with a custom focus question.
If the secrets aren't configured the workflow exits quietly without failing.

To change the schedule, edit the `cron:` line (times are UTC). ESPN cookies
last roughly a year, so expect to refresh the `ESPN_S2` / `SWID` secrets
once a season.

## Cost

Each report is a single Claude call with roughly 5–15K input tokens and a
1–2K token report. On `claude-opus-4-8` ($5 / $25 per million tokens) that's
about **$0.05–0.15 per report** — a few dollars a month at daily cadence.
Pass `--model claude-sonnet-5` for a cheaper (still strong) option.

## Notes

- The advisor is read-only: it never makes moves for you. Pair it with
  `espn-fb add` / `espn-fb optimize --apply` when you want to act on it.
- Recommendations are grounded in the ESPN data included in the snapshot;
  the model is instructed not to invent stats and to only suggest players
  actually in the free-agent pool.
