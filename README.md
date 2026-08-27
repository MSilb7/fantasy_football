# Fantasy Football Assistant

A local-first decision-support system for ESPN fantasy football leagues. The goal is to give a
prompting assistant durable knowledge of league rules, rosters, player performance, transactions,
manager tendencies, and your preferences so it can help with drafts, trades, free agency, lineup
setting, and related decisions.

The original payout calculator is preserved as a separate application under `apps/payouts/`.

## Repository map

```text
apps/payouts/                 Preserved year-by-year payout notebooks and local reports
config/                       Local league profiles (example committed; real profile ignored)
data/raw/                     Immutable source payloads (ignored except .gitkeep)
data/normalized/              Stable internal snapshots (ignored except .gitkeep)
docs/product/PRD.md           Product vision, capabilities, stories, and roadmap
docs/technical/               Maintained implementation map and decisions
src/fantasy_assistant/        Reusable package and ESPN adapter
tests/                        Offline contract fixtures and unit tests
```

## Quick start

The core sync path uses only the Python 3.11+ standard library.

```bash
cp config/leagues.example.toml config/leagues.toml
cp .env.example .env
```

Fill in league metadata in `config/leagues.toml` and private ESPN cookies in `.env`, then run:

```bash
PYTHONPATH=src python -m fantasy_assistant.cli doctor
PYTHONPATH=src python -m fantasy_assistant.cli sync-league --league primary --season 2026
```

The sync stores both the untouched ESPN response and a source-neutral normalized snapshot. Neither
local league data nor credentials are committed.

To install the command and optional payout notebook dependencies:

```bash
python -m pip install -e '.[payouts]'
fantasy-assistant doctor
```

## Tests

No live ESPN account is required for the current test suite:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Product direction

The living product definition is `docs/product/PRD.md`; implementation boundaries live in
`docs/technical/TECHNICAL_DESIGN.md`. These are the canonical starting points for future prompting
sessions so decisions and context compound instead of being rediscovered.
