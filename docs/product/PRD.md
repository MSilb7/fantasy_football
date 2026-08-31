# PRD — Fantasy Football Assistant

**Status date:** 2026-08-31
**Status legend:** **BUILT** · **PARTIAL** · **UNBUILT** · **DECLINED**

This is the single living product north star. It owns desired behavior and priorities; technical
implementation lives in `docs/technical/TECHNICAL_DESIGN.md`.

## 1. Vision

**One-liner:** A private, context-rich assistant that turns league state, player evidence, manager
behavior, and the user's preferences into timely fantasy football decisions.

The primary user manages one or more ESPN fantasy football teams and interacts through natural
language. A good answer understands the exact league rules and roster, distinguishes facts from
forecasts, explains trade-offs, and can be refreshed as the draft or season changes.

### Non-goals

- Automatically execute drafts, waiver claims, trades, or lineup changes in v1.
- Treat projections, news, or manager-behavior predictions as certainty.
- Commit ESPN credentials, private league payloads, or personal preference data to git.
- Make payout money movement; the preserved payout application produces reports only.

## 2. Principles

- **League-specific before generic** — scoring, roster slots, keepers, draft state, and opponent
  behavior materially change recommendations.
- **Evidence before confidence** — every recommendation distinguishes observed data, assumptions,
  projections, and judgment.
- **Current state is timestamped** — advice identifies the snapshot and freshness it relies on.
- **One ingestion path** — ESPN access and normalization are reusable infrastructure, not copied
  feature logic.
- **Raw evidence is immutable** — original source payloads remain available for auditing and
  reprocessing.
- **Private by default** — credentials, league data, manager profiles, and user preferences stay
  local unless the user explicitly chooses another storage boundary.
- **Human decides** — the assistant recommends and explains; the user approves consequential moves.
- **Behavioral models stay humble** — opponent tendencies are probabilistic, evidence-linked, and
  easy to revise as new actions arrive.

## 3. Capabilities

### Existing payout application

- Fetch ESPN teams, matchups, scores, standings, and settings in annual notebooks — **PARTIAL**
- Calculate fully funded weekly-high and playoff payout reports — **BUILT**
- Export an auditable multi-tab workbook — **BUILT**

### Shared data foundation

- Discover current football league and team memberships from the authenticated ESPN profile —
  **BUILT**
- Load multiple named league profiles without storing secrets in git — **BUILT**
- Resolve season-specific league/team identities and continue historical sync across inaccessible
  seasons — **BUILT**
- Validate local ESPN credentials without printing them — **BUILT**
- Fetch reusable ESPN league snapshots through one client — **BUILT**
- Normalize league settings, managers, teams, rosters, and matchups — **BUILT**
- Store timestamped raw and normalized snapshots locally — **BUILT**
- Ingest current and historical ESPN draft selections — **BUILT**
- Ingest ESPN availability, ADP, draft ranks, projections, injuries, and prior-season actual stats —
  **BUILT**
- Ingest historical transactions and player news — **UNBUILT**
- Detect snapshot changes and maintain a queryable longitudinal league history — **UNBUILT**

### Decision support

- Build a league-aware draft board from roster and scoring rules — **BUILT**
- Refresh and update draft recommendations after every pick — **BUILT**
- Evaluate trades using roster construction, replacement value, schedule, risk, and preferences —
  **UNBUILT**
- Rank free agents and proposed waiver bids — **UNBUILT**
- Recommend legal lineups with floor/upside scenarios and late-news flags — **UNBUILT**
- Explain recommendations in prompt-ready context bundles with source timestamps — **UNBUILT**

### Learning and personalization

- Store explicit risk tolerance, roster-construction preferences, and decision history — **UNBUILT**
- Learn manager tendencies from drafts, transactions, lineup choices, and trades — **UNBUILT**
- Evaluate prior recommendations against outcomes without hindsight leakage — **UNBUILT**

## 4. User stories

- **US-1.1 · Preserve payouts** — As the commissioner, I can run the historical payout workflow
  independently from decision-support development. — **BUILT**
- **US-1.2 · Onboard a league** — As the user, I can provide league ID, team identity, seasons, and
  private credentials once, then validate the setup safely. — **BUILT**
- **US-1.3 · Refresh league context** — As the user, I can fetch a timestamped league snapshot that
  includes rules, teams, rosters, owners, and matchups. — **BUILT**
- **US-1.4 · Refresh player evidence** — As the user, I can ingest current and historical stats,
  projections, availability, and news with source and timestamp metadata. — **PARTIAL**
- **US-2.1 · Prepare a draft** — As the user, I can receive a league-specific tiered draft plan after
  providing draft slot, keepers, and strategy preferences. The live board covers rules, slot,
  keepers, and roster construction; explicit strategy preferences and durable tiers remain. — **PARTIAL**
- **US-2.2 · Run a live draft** — As picks occur, I can update draft state and get a short list of
  best next selections plus likely intervening demand. Each answer defaults to a score-sorted top 10
  with projected points and 0–100 value, need, scarcity, opponent-demand, next-turn availability,
  health, and overall ratings. Refresh and computation should complete within 10 seconds under
  ordinary ESPN availability; calibrated player-level predictions for intervening picks remain. — **PARTIAL**
- **US-3.1 · Evaluate a trade** — As the user, I can compare a trade's expected value, risks, roster
  effects, and acceptance likelihood. — **UNBUILT**
- **US-3.2 · Work waivers** — As the user, I can prioritize adds/drops and waiver budget using league
  scarcity and opponent needs. — **UNBUILT**
- **US-3.3 · Set a lineup** — As the user, I can receive a valid lineup recommendation with explicit
  floor, median, ceiling, injury, and timing considerations. — **UNBUILT**
- **US-4.1 · Learn preferences** — As the user, I can correct or explain a decision and have that
  preference reflected in later recommendations. — **UNBUILT**
- **US-4.2 · Model managers** — As the user, I can see evidence-based estimates of how another manager
  may draft, bid, trade, or set a lineup. — **UNBUILT**

## 5. Roadmap

1. **League onboarding and data contracts** — auto-discovery, season-specific identity overrides,
   resilient historical sync, and real 2026 league validation are built; continue capturing
   materially new ESPN shapes as fixtures. Supports US-1.2 and US-1.3.
2. **Player evidence layer** — ESPN baseline availability, ADP, ranks, projections, injuries, and
   prior-season actuals are built; add news, deeper history, source comparison, identity
   reconciliation, and confidence. Supports US-1.4.
3. **Draft workspace** — the live top-10 board, roster constraints, positional scarcity/value,
   opponent-demand estimates, and pick refresh are built; add durable tiers, preferences, richer
   injury evidence, and calibrated player-level intervening-pick predictions. Supports US-2.1 and
   US-2.2 and is the first decision workflow.
4. **In-season decisions** — implement lineup, waiver, and trade analysis on the same context model.
   Supports US-3.1 through US-3.3.
5. **Preference and manager learning** — retain decisions and outcomes, then introduce calibrated
   behavioral features with uncertainty. Supports US-4.1 and US-4.2.
6. **Payout maintenance** — keep the shared, regression-tested allocation contract and preserved
   notebook workflow current as league rules change. Supports US-1.1.

## 6. Live state

- Local league metadata: ignored `config/leagues.toml`; template at `config/leagues.example.toml`.
- Raw ESPN observations: ignored `data/raw/espn/<league>/<season>/<timestamp>.json`.
- Normalized observations: ignored `data/normalized/espn/<league>/<season>/<timestamp>.json`.
- Pick-level draft observations: ignored `data/{raw,normalized}/espn-draft/...`.
- ESPN player evidence: ignored `data/{raw,normalized}/espn-player-evidence/...`.
- Generated payout reports: ignored `apps/payouts/outputs/`.
- Queue status: `node scripts/compounding-status.mjs`.

## 7. Open product decisions

- Which external sources should complement ESPN's baseline for deeper historical stats, projections,
  injuries, ADP, and news?
- What are the user's draft philosophy, risk tolerance, keeper rules, and trade/waiver preferences?
- Should prompt interaction remain repository-local, or later gain a dedicated chat/UI surface?

## 8. Maintenance

Read this document at the start of product work. Update a story before implementing genuinely new
behavior, reconcile status against tests and code, and route unresolved drift to `docs/compounding/`.
Keep technical detail and architectural rationale in their dedicated documents rather than copying
them here.
