# Cookbook

Practical recipes for common ESPN fantasy baseball workflows. All
snippets assume you've built a `League`:

```python
from espn_fantasy_baseball import League

lg = League(league_id=123456, year=2024, espn_s2="...", swid="{...}")
```

---

## Standings

### Print the standings table

```python
for rank, team in enumerate(lg.standings(), 1):
    print(f"{rank:>2}. {team.name:<25}  {team.record}  PF={team.points_for:.1f}")
```

### Biggest overachievers (wins vs. points-for)

```python
teams = lg.teams()
# Sort by actual record vs. what their PF would predict.
by_record = sorted(teams, key=lambda t: t.wins, reverse=True)
by_pf = sorted(teams, key=lambda t: t.points_for, reverse=True)
for team in teams:
    record_rank = by_record.index(team) + 1
    pf_rank = by_pf.index(team) + 1
    luck = pf_rank - record_rank
    print(f"{team.name:<25}  record #{record_rank}  PF #{pf_rank}  luck={luck:+d}")
```

---

## Matchups & boxscores

### Score the current week

```python
for m in lg.scoreboard():
    home = lg.team(m.home_team_id).name
    away = lg.team(m.away_team_id).name
    print(f"  {away:<25} {m.away_score:>7.1f}  @  {m.home_score:<7.1f} {home}")
```

### Highest-scoring player of the week

```python
best_player, best_points = None, 0.0
for box in lg.boxscores(matchup_period=12):
    for entry in box.home_lineup + box.away_lineup:
        if entry.points > best_points:
            best_player, best_points = entry.player, entry.points
print(f"Top performer: {best_player.name} — {best_points:.1f} pts")
```

### All pitcher lines from one matchup

```python
box = lg.boxscores(matchup_period=12)[0]
for entry in box.home_lineup + box.away_lineup:
    if entry.player.is_pitcher():
        s = entry.stats
        print(f"{entry.player.name:<25} IP={s.get('IP',0)}  K={s.get('K',0)}  ERA={s.get('ERA',0):.2f}")
```

---

## Rosters

### Whose IL is most stacked?

```python
import itertools

for team in lg.teams():
    injured = team.injured()
    if injured:
        names = ", ".join(p.name for p in injured)
        print(f"{team.name:<25}  {len(injured)}  ({names})")
```

### All shortstop-eligible players across every roster

```python
ss_candidates = [
    (team.name, p.name)
    for team in lg.teams()
    for p in team.roster
    if "SS" in p.eligible_positions
]
for team_name, player_name in ss_candidates:
    print(f"{team_name:<25}  {player_name}")
```

### Position-scarcity snapshot

```python
from collections import Counter

rostered = Counter()
for team in lg.teams():
    for p in team.roster:
        for pos in p.eligible_positions:
            rostered[pos] += 1
for pos, n in rostered.most_common():
    print(f"{pos:<6} {n}")
```

---

## Free agents / waivers

### Top 25 free agents by last-7 points

```python
for p in lg.free_agents(size=25, sort_by="last7_points"):
    print(f"{p.name:<25} {p.pro_team:<4}  owned={p.percent_owned:5.1f}%")
```

### Find a streaming starter for today

```python
today = 115  # scoring period id (ESPN daily period)
starters = lg.free_agents(size=25, position="SP", scoring_period=today)
for sp in starters:
    print(sp.name, sp.pro_team, sp.percent_owned)
```

### Replacement-level baseline at each position

```python
import statistics

for pos in ["C", "1B", "2B", "SS", "3B", "OF", "SP", "RP"]:
    fas = lg.free_agents(size=50, position=pos, sort_by="season_points")
    totals = [
        p.season_stats().get("appliedTotal", 0)  # if your league surfaces it
        for p in fas[:10]
    ]
    if totals:
        print(f"{pos:<4}  replacement ≈ {statistics.mean(totals):.1f}")
```

---

## Draft

### Show the draft board in pick order

```python
for pick in lg.draft():
    label = pick.player_name or f"player#{pick.player_id}"
    bid = f" ${pick.bid_amount}" if pick.bid_amount is not None else ""
    keeper = " (keeper)" if pick.keeper else ""
    print(f"R{pick.round:>2}.{pick.round_pick:<2} (#{pick.overall_pick:>3})  team {pick.team_id}  {label}{bid}{keeper}")
```

### Auction-spend distribution

```python
from collections import defaultdict

spend = defaultdict(int)
for pick in lg.draft():
    if pick.bid_amount is not None:
        spend[pick.team_id] += pick.bid_amount
for tid, total in sorted(spend.items(), key=lambda kv: -kv[1]):
    print(f"team {tid}: ${total}")
```

---

## League settings

### Print scoring rules

```python
for item in lg.settings().scoring:
    tag = " (reverse)" if item.is_reverse else ""
    print(f"{item.stat_name:>5}  {item.points:+6.2f}{tag}")
```

### Count roster slots and total roster size

```python
s = lg.settings()
print(f"{s.name} — {s.size}-team {s.scoring_type}")
total = 0
for slot, n in s.roster_slots.items():
    print(f"  {slot:<5}  {n}")
    total += n
print(f"  ---")
print(f"  total: {total}")
```

---

## Transactions

### Recent activity feed

```python
for event in lg.recent_activity(size=20):
    ts = event.date.strftime("%Y-%m-%d %H:%M") if event.date else "?"
    print(f"{ts}  {event.type}")
    for a in event.actions:
        print(f"    team={a.team_id}  {a.type:<12}  player#{a.player_id}")
```

---

## Advanced

### Use a pre-configured session (proxy, custom timeout, etc.)

```python
import requests

session = requests.Session()
session.proxies = {"https": "http://corp-proxy:3128"}
session.headers["User-Agent"] = "my-tool/1.0"

lg = League(
    league_id=123456, year=2024,
    session=session,
    timeout=10.0,
    max_retries=5,
)
```

### Query multiple seasons

```python
for year in range(2020, 2025):
    lg = League(123456, year, espn_s2=S2, swid=SWID)
    champ = lg.standings()[0]
    print(f"{year}: {champ.name} ({champ.record})")
```

### Export a league snapshot to JSON

```python
import json

snapshot = {
    "settings": lg.settings().raw,
    "teams":    [t.raw for t in lg.teams()],
    "schedule": [m.raw for m in lg.schedule()],
}
with open("snapshot.json", "w") as f:
    json.dump(snapshot, f, default=str, indent=2)
```

### Plug in your own HTTP transport

```python
from espn_fantasy_baseball import ESPNClient, League

class LoggingSession:
    def __init__(self, inner):
        self.inner = inner
        self.cookies = inner.cookies
        self.headers = inner.headers
    def request(self, method, url, **kw):
        print("→", method, url)
        return self.inner.request(method, url, **kw)

import requests
client = ESPNClient(123456, 2024, session=LoggingSession(requests.Session()))
lg = League(123456, 2024, client=client)
```
