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

Check `python --version` before live operations. Some local login shells may resolve `python` or
`python3` to an older Anaconda interpreter even when a newer Homebrew/system interpreter is
installed; run the commands with an explicit Python 3.11+ executable when that happens.

Create `.env` from the example and fill in private ESPN cookies. Then discover football leagues and
generate the ignored local profile file directly from the authenticated ESPN account:

```bash
cp .env.example .env
PYTHONPATH=src python -m fantasy_assistant.cli discover-leagues --season 2026 --write-config
PYTHONPATH=src python -m fantasy_assistant.cli doctor
PYTHONPATH=src python -m fantasy_assistant.cli sync-league --league primary --season 2026
PYTHONPATH=src python -m fantasy_assistant.cli sync-draft --league primary --season 2026
PYTHONPATH=src python -m fantasy_assistant.cli sync-player-evidence --league primary --season 2026
PYTHONPATH=src python -m fantasy_assistant.cli draft-board --league primary --season 2026 --refresh
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

During a live snake draft, run `draft-board --refresh` for each decision. It refreshes only the
pick-level state, excludes keepers and completed selections, reconstructs every team's positional
needs, and prints a score-sorted top 10. The table includes league-scoring projected points plus
0–100 ratings for consensus value, your roster need, positional scarcity, opponent demand before
your next decision, chance the player is gone by then, health, and overall recommendation strength.
Refresh league settings and player evidence once before the draft; the per-pick command then stays
small enough for a normal draft clock.

In a fresh Codex task opened on this repository, the short prompt **`run now`** (or **`on the
clock`**) invokes the repository-local live draft companion. It performs the same refresh and
returns the current top-10 table; the user still makes the selection in ESPN.

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
