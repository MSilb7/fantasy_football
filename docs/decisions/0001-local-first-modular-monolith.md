# ADR-0001: Start as a local-first modular monolith

- **Status:** Accepted
- **Date:** 2026-08-27

## Context

The product will combine private ESPN league data, external player evidence, user preferences, and
interactive decision workflows. It needs clear reusable boundaries now, but does not yet need the
operational cost of services, queues, a hosted UI, or remote persistence.

## Decision

Build one installable Python package with explicit source adapters, normalization, persistence, and
future decision modules. Operate it locally through a CLI, prompting agents, and the preserved payout
notebooks. Keep provider-specific response shapes outside decision logic.

## Consequences

- Early workflows share code and data contracts without networked-service overhead.
- Private context remains on the user's machine by default.
- Module boundaries must remain deliberate so a later UI or service can reuse them.
- Scheduling, collaboration, remote access, and high-concurrency concerns are deferred until a real
  workflow requires them.
