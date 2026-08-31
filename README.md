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

Create `.env` from the example and fill in private ESPN cookies. Then discover football leagues and
generate the ignored local profile file directly from the authenticated ESPN account:

```bash
cp .env.example .env
PYTHONPATH=src python -m fantasy_assistant.cli discover-leagues --season 2026 --write-config
PYTHONPATH=src python -m fantasy_assistant.cli doctor
PYTHONPATH=src python -m fantasy_assistant.cli sync-league --league primary --season 2026
PYTHONPATH=src python -m fantasy_assistant.cli sync-draft --league primary --season 2026
PYTHONPATH=src python -m fantasy_assistant.cli sync-player-evidence --league primary --season 2026
PYTHONPATH=src python -m fantasy_assistant.cli sync-history --league primary
```

`discover-leagues` reports league/team identity and draft metadata but never writes cookies. If ESPN
discovery is unavailable, copy `config/leagues.example.toml` to `config/leagues.toml` and fill it in
manually. Replace `primary` in the sync command with a generated profile name shown by `doctor`.

Each sync stores both the untouched ESPN response and a source-neutral normalized snapshot. League
sync retains each league's scoring, roster, keeper, and draft-order settings. Draft sync separates
ESPN's unfilled future slots from real selections, and player-evidence sync captures league-relative
availability, ADP, ranks, projections, injury state, and historical actual stats. Neither local
league data nor credentials are committed.

Historical sync uses the profile's `seasons` list and continues when ESPN returns an inaccessible
year, leaving earlier snapshots unchanged. If ESPN changed a league or team ID between seasons, add
the season-specific override shown in `config/leagues.example.toml`; credentials remain shared in
`.env` and are never duplicated in the profile.

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
