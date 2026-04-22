# Contributing

Thanks for your interest! This project aims to be the most approachable
Python client for ESPN Fantasy Baseball.

## Setup

```bash
git clone https://github.com/anthonysawah/espn-fantasy-baseball-api
cd espn-fantasy-baseball-api
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Workflow

1. **Open an issue first** for anything larger than a small bug-fix so we
   can align on approach.
2. Write a failing test first when practical — fixtures live in
   `tests/fixtures/` and mimic real ESPN payload shapes.
3. Run `ruff check .`, `mypy espn_fantasy_baseball`, `pytest`.
4. Keep PRs focused. One logical change per PR.

## Adding a new ESPN endpoint / view

- Add a fixture to `tests/fixtures/` captured from a real response (scrub
  any personal identifiers).
- Add the view constant to `espn_fantasy_baseball/constants.py`.
- Build a resource dataclass in `espn_fantasy_baseball/resources/` if the
  payload warrants it.
- Expose a method on `League`.
- Add the route to `tests/conftest.py`'s fixture and write tests.

## Decoding numeric ids

Whenever ESPN returns a numeric id (stat ids, slot ids, proTeamId, etc.)
we decode it to a human-readable abbreviation via the maps in
`constants.py`. If you find an id that isn't mapped, add it there.

## Code style

- Type hints everywhere.
- Dataclasses for payload-shaped records, with a `from_raw` classmethod.
- Keep dependencies minimal. Only `requests` at runtime.
