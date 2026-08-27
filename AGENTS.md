# Shared repository guidance

## Mission and sources of truth

- Read `docs/product/PRD.md` before product work. Update its stories or roadmap when a confirmed
  product decision changes desired behavior.
- Read `docs/technical/TECHNICAL_DESIGN.md` before changing component boundaries, data ownership,
  interfaces, secrets handling, or runtime behavior. Reconcile it in the same change.
- Decision records in `docs/decisions/` own architectural rationale. Code, tests, snapshots, and
  generated artifacts own exact executable details.
- `apps/payouts/` is a preserved application. Do not change payout math without an offline
  regression fixture that proves the intended financial result.

## Engineering rules

- Keep ESPN-specific fields and HTTP behavior inside `src/fantasy_assistant/espn/` and ingestion
  normalization. Decision modules consume normalized models, not ad hoc ESPN dictionaries.
- Add shared behavior to `src/fantasy_assistant/`; do not duplicate API calls across notebooks or
  feature-specific scripts.
- Treat raw snapshots as immutable evidence. Schema changes create a new normalized schema version
  or an explicit migration; they never rewrite raw source payloads.
- Credentials belong only in environment variables or the ignored `.env`. League profiles and
  generated data are local by default. Never print cookie values or commit personal league data.
- Prefer deterministic, explainable recommendations that retain their inputs and assumptions.
  Predictions about other managers must include confidence and evidence, not unsupported labels.
- Keep core ingestion dependency-light. Add a dependency only when it materially simplifies a
  maintained capability.

## Validation and closure

- Run `PYTHONPATH=src python -m unittest discover -s tests -v` for core changes.
- Run `node scripts/compounding-status.mjs` at session start when the script is present; capture
  important gaps under `docs/compounding/` rather than leaving them only in chat.
- Before ending substantive work, reconcile product and technical docs, run relevant checks, inspect
  git state for stranded work, and either complete each follow-up or record it with acceptance
  criteria in the compounding queue.
- Repeated repository procedures belong in a repository-local skill; broadly reusable procedures
  should be promoted to the canonical AI Tools repository rather than copied into this file.
