# ADR-0002: Preserve immutable raw snapshots and version normalized data

- **Status:** Accepted
- **Date:** 2026-08-27

## Context

ESPN's interface is not controlled by this repository, player-data sources may disagree, and future
recommendations must be explainable against the information available at the time. Storing only a
latest transformed table would make schema changes and historical evaluation difficult to audit.

## Decision

Persist each external fetch as an immutable, timestamped raw snapshot and create a parallel
normalized snapshot with an explicit schema version. Derived recommendations will reference source
snapshots and as-of times. Raw data is never rewritten during normalization changes.

## Consequences

- Source evidence can be reprocessed and contract drift can be diagnosed.
- Storage grows over time, so retention and backup policy will eventually be required.
- Sensitive league data remains gitignored and local by default.
- Identity reconciliation and migrations must be explicit as sources and schemas expand.
