# Technical Design — Fantasy Football Assistant

**Purpose:** Map how the implementation satisfies `docs/product/PRD.md` without duplicating exact
schemas or historical rationale.
**Last reconciled:** 2026-08-27 · `codex/assistant-foundation`

## 1. System context and traceability

The system is a local Python modular monolith operated through prompts, a CLI, and the preserved
Jupyter payout application. ESPN is the initial league system of record. Future player-data sources
will enter through separate adapters and converge on versioned normalized records before any
decision module uses them.

This design currently implements PRD US-1.1 through US-1.3. Draft and in-season analysis remain
planned. The system does not execute moves on ESPN and has no remote service or shared database.

## 2. Components and responsibilities

| Component | Responsibility | Owns | Interface | Product links | Status |
|---|---|---|---|---|---|
| `apps/payouts/` | Preserve annual payout workbook workflow | Notebook presentation, ESPN retrieval, and reports | Jupyter notebooks | US-1.1 | BUILT |
| `src/fantasy_assistant/payouts.py` | Allocate the total buy-in pot across every payout | Financial calculation and conservation invariant | `PayoutRules`, `calculate_payout_plan` | US-1.1 | BUILT |
| `src/fantasy_assistant/config.py` | Load local league metadata and private ESPN cookies | Configuration validation and secret-name compatibility | `load_league_profiles`, `load_espn_credentials` | US-1.2 | BUILT |
| `src/fantasy_assistant/espn/` | Isolate ESPN URLs, views, cookies, filters, and transport failures | ESPN source contract | `ESPNClient.fetch_league` | US-1.3 | BUILT |
| `src/fantasy_assistant/ingestion/normalize.py` | Convert ESPN payloads to a stable source-neutral snapshot | Normalized schema v1 | `normalize_league_snapshot` | US-1.3 | BUILT |
| `src/fantasy_assistant/ingestion/store.py` | Persist immutable raw and normalized observations | Timestamped local JSON snapshots | `SnapshotStore.save` | US-1.3 | BUILT |
| `src/fantasy_assistant/cli.py` | Expose safe setup checks and sync orchestration | Human/agent command contract | `doctor`, `sync-league` | US-1.2, US-1.3 | BUILT |
| Future player-source adapters | Ingest stats, projections, news, injuries, and ADP | Source-specific evidence | Provider contracts to be decided | US-1.4 | PLANNED |
| Future decision modules | Produce draft, trade, waiver, and lineup recommendations | Derived features and explanations | Prompt-ready context and recommendation contracts | US-2.*, US-3.* | PLANNED |
| Future behavior store | Retain decisions, outcomes, preferences, and manager actions | Longitudinal evidence | Versioned event/feature contract | US-4.* | PLANNED |

## 3. Data ownership and persistence

- ESPN owns the upstream league state. Each raw response is stored unchanged under
  `data/raw/espn/<league>/<season>/<timestamp>.json` and is append-only evidence.
- Normalization owns schema v1 under the parallel `data/normalized/` path. Exact fields are defined
  by `normalize_league_snapshot` and pinned by `tests/fixtures/league_minimal.json`.
- `config/leagues.toml` owns local league identity and team mapping. It is ignored because those
  details may be private even though they are not authentication secrets.
- `.env` or the process environment owns ESPN cookies. Cookie values never enter stored snapshots,
  logs, config profiles, or exception text.
- `src/fantasy_assistant/payouts.py` owns financial allocation. The fixed third-place amount and
  weekly-highs pool are removed from total buy-ins before first and second split the remainder.
  Generated notebook reports are ignored local artifacts.
- No query database exists yet. A longitudinal store must be chosen before transaction history,
  recommendation history, or behavioral features are implemented.

## 4. Interfaces and contracts

`ESPNClient.fetch_league` accepts a season, league ID, view set, and optional matchup periods. The
default view set centralizes the currently needed team, roster, settings, matchup, score, and
standings data. Transport failures raise sanitized `ESPNAPIError` messages.

Normalized schema v1 contains snapshot metadata, league identity/status, selected rules, members,
teams with current roster entries, and matchups. ESPN identifiers are retained for joins, but later
decision modules should not reach back into raw dictionaries for ordinary fields.

The CLI returns zero on success and two on configuration, transport, or storage errors. `doctor`
validates presence, not whether ESPN accepts an expiring cookie. `sync-league` is the first live
credentialed contract and must be validated against a user-provided league before it is considered
production-complete.

## 5. Important flows

### League onboarding and sync

1. The user copies the example profile and credential files and fills them locally.
2. `doctor` parses profiles and confirms both credential values are present without displaying them.
3. `sync-league` selects a profile and asks the ESPN adapter for one multi-view payload.
4. The raw response is normalized in memory.
5. The store writes raw and normalized JSON atomically to timestamped paths.
6. Later decision modules load normalized snapshots and state their source timestamp.

Failure before step 5 produces no completed snapshot. The store writes through a temporary file and
an atomic same-directory replacement so interrupted writes do not masquerade as valid observations.

### Future recommendation flow

The target flow is: refresh sources → reconcile identities/timestamps → derive league-relative
features → generate candidate actions → score scenarios and uncertainty → produce an explanation
bundle → user decides → retain decision and eventual outcome. No step after source refresh is built.

## 6. Security and trust boundaries

- ESPN cookies grant private-league access and are high-sensitivity secrets. They stay in ignored
  local configuration, travel only in the HTTPS `Cookie` request header, and are redacted from object
  representations and errors.
- ESPN and future third-party payloads are untrusted external input. Normalization tolerates missing
  optional fields; new shapes require fixture-backed changes.
- League data can expose names, rosters, and manager behavior. Raw, normalized, preference, and
  behavioral data remain local and gitignored by default.
- Prompt-generated recommendations are advisory. There is no write adapter to ESPN, payment system,
  email, or messaging service.

## 7. Runtime topology and operations

Python 3.11+ runs locally. Core ingestion has no third-party runtime dependency. The payout notebooks
use the optional `payouts` dependency group. There is no deployment unit, scheduler, or background
process.

Operator commands:

```bash
PYTHONPATH=src python -m fantasy_assistant.cli doctor
PYTHONPATH=src python -m fantasy_assistant.cli sync-league --league primary --season 2026
PYTHONPATH=src python -m unittest discover -s tests -v
node scripts/compounding-status.mjs
```

Snapshots are the current observability and recovery mechanism: raw evidence can be renormalized if
the schema changes. Retention and backup policy are not yet defined.

## 8. Testing and verification strategy

- Unit tests cover profile/credential precedence, redaction, normalization, immutable snapshot paths,
  and path safety.
- A synthetic ESPN fixture pins current response assumptions without leaking a real league.
- A deterministic payout fixture proves exact allocations and total-pot conservation, while a
  notebook contract test prevents the 2025 presentation from reintroducing copied payout math.
- No live contract test exists because it would require expiring private credentials. The onboarding
  milestone should capture a sanitized fixture from each materially different league configuration.
- Draft, trade, waiver, lineup, and behavioral evaluation harnesses are not yet built.

## 9. Active decisions

| Decision | Governs | Status | Record |
|---|---|---|---|
| ADR-0001 · Local-first modular monolith | Runtime and component boundaries | ACTIVE | `docs/decisions/0001-local-first-modular-monolith.md` |
| ADR-0002 · Immutable raw and versioned normalized snapshots | Data ownership and auditability | ACTIVE | `docs/decisions/0002-immutable-source-snapshots.md` |

## 10. Known technical gaps and evolution

| Item | Product link | Current state | Target state | Tracking |
|---|---|---|---|---|
| Real ESPN contract validation | US-1.3 | Synthetic fixture only | Sanitized fixtures for actual league shapes | PRD roadmap 1 |
| Player evidence ingestion | US-1.4 | No provider contract | Timestamped multi-source evidence with identity reconciliation | PRD roadmap 2 |
| Queryable history | US-1.4, US-4.* | JSON snapshots only | Local analytical store with migrations | Open decision |
| Draft engine | US-2.* | Absent | League-aware, stateful draft recommendations | PRD roadmap 3 |

## 11. Authoritative pointers

| Exact truth | Source or command |
|---|---|
| Package and optional dependencies | `pyproject.toml` |
| Payout allocation contract | `src/fantasy_assistant/payouts.py` and `tests/fixtures/payout_plan.json` |
| ESPN request contract | `src/fantasy_assistant/espn/client.py` |
| Normalized schema v1 | `src/fantasy_assistant/ingestion/normalize.py` and its fixture test |
| Snapshot path contract | `src/fantasy_assistant/ingestion/store.py` |
| Local runtime state | ignored `config/leagues.toml`, `data/`, and `apps/payouts/outputs/` |
| Test contract | `PYTHONPATH=src python -m unittest discover -s tests -v` |

## 12. Maintenance protocol

Reconcile this index whenever a component boundary, data owner, interface, security assumption,
runtime behavior, or operational command changes. Product meaning stays in the PRD, historical
rationale stays in decision records, and exact schemas stay in executable sources and tests.
