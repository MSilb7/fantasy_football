<!-- compounding-system: v8 — installed from claude_tools; do not hand-edit; run /compounding upgrade -->
# Compounding SOP — Continuously-Discovered Improvements

Any session — scheduled routine, build agent, research thread — that encounters something worth
fixing writes a scoped entry here. The goal is a structured queue that any agent can surface to the
operator ("I see 3 OPEN items — want to tackle any?"), that a bounded worker can drain autonomously
once an item's acceptance criteria are firm.

*Canonical system:* this SOP, the selector (`scripts/compounding-status.mjs`), the portable
`compounding-drain` skill, and the auto-merge workflow are installed and upgraded by
the global `/compounding` skill (`github.com/MSilb7/claude_tools`). The reference implementation
lives in `MSilb7/investment-agent` (which uses a native TypeScript selector — behavior is identical).

---

## The system's skills (and the naming convention)

Every command that belongs to the compounding system is namespaced under **`compounding`** — that is
the convention, and it is load-bearing: the shared prefix is how a session, a routine, or a fresh
agent knows a command is part of this one system (and what to `/compounding upgrade` together).

**Naming convention (applies to any system, not just this one):** a command that belongs to a system
carries the `<system>-<verb>` prefix; the **bare `<system>`** command is the system's root (an
installer / multiplexer with modes). Follow this when you add a command to a system — a new
compounding command is `compounding-<verb>`, never a bare verb that hides its membership. Do NOT
prefix a command that merely *touches* the system's artifacts but belongs to a broader concern (e.g. a
general "capture a learning" skill that writes to several destinations is not `compounding-capture` —
prefixing it would falsely claim system membership).

| Command | What it is | When a session/agent/routine uses it |
|---|---|---|
| `/compounding` | Root skill — `setup` / `upgrade` / `status` modes | Install the system in a repo; sync a repo to the latest templates; one-off status |
| `/compounding-drain` | The bounded worker — drains up to three eligible items, one at a time | On the repository-approved cadence, or on demand ("work the next improvement items") |
| `/compounding-curate` | Context-lifecycle pass — dedup / compress / promote / retire the always-on context | The weekly hygiene routine, or on demand when AGENTS.md / standing practices have grown heavy |
| `compounding-status` | The selector — derives each item's state (ELIGIBLE / IN-PROGRESS / …) | Session start (surface OPEN items); the drain's STEP 1; `/compounding status` |
| *capture* (inline) | Writing a `docs/compounding/YYYY-MM-DD-HHMM.md` entry | Any session that hits something fixable — see "When to write" below (no command; it's a plain file write) |
| `/prd-reconcile` | Reconcile the product PRD (`docs/product/PRD.md`) against reality — the north-star doc's desired-vs-actual pass | On a cadence (weekly hygiene) or on demand ("is the product doc current?") |
| `maintain-technical-design` | Create or reconcile the technical index (`docs/technical/TECHNICAL_DESIGN.md`) against code, decisions, the PRD, and runtime evidence | After material architecture changes, on a cadence, or when a repository lacks an implementation map |

**Three pillars.** This system maintains three distinct living sources, reconciled against reality at their own
altitudes: the **improvement queue** (`docs/compounding/`) captures *what to fix*; the **product PRD**
(`docs/product/PRD.md`) captures *what the product does, for whom, and why*; and the **technical design**
(`docs/technical/TECHNICAL_DESIGN.md`) maps *how the implementation satisfies that intent*. Decision records
preserve why significant choices were made. Code, migrations, schemas, generated specifications, tests, and
runtime inspection remain the exact executable truth.

New to the system? Read this table, then "When to write" (how to file), the "Item format" (the
contract), and "Validating a fix" (how a fix is proven). Those four are the whole operating manual.

---

## When to write a compounding doc

Write an entry whenever any session:
- Hits an error it worked around (the workaround will bite next time)
- Observes silent or partial output that could mislead a future run or operator
- Encounters an undocumented format or interface it had to reverse-engineer from source
- Notices a logging/observability gap that makes post-hoc diagnosis harder
- Surfaces a reconciliation gap (state vs expectation, doc vs reality)
- Learns something non-obvious that should change how we build or operate
- Encounters a non-obvious multi-step procedure for the second time, or a repeated workflow that should
  become a repository-local skill (or a canonical AI Tools skill via `promote-skill` when it generalizes)
- **Finds a SIMPLIFICATION opportunity** (*simplicity is a first-class compounding dimension*) —
  the same knowledge duplicated across N docs (collapse to ONE canonical home + pointers;
  duplication is how copies go stale and parallel sessions collide), a procedure that has accreted
  steps no longer paying rent, a dual-format/legacy path whose deprecation window has passed, or any
  place where making a complicated thing simple beats adding another guard on top of it. When the
  simplification is small and safe, **just do it inline** (same rule as low-risk fixes); file an
  entry only when it needs a decision or real effort.

Do NOT write entries for clean runs with no observations — signal-to-noise matters.

---

## File naming

```
docs/compounding/YYYY-MM-DD-HHMM.md
```

One file per session. Multiple items go in the same file. If nothing noteworthy happened, no file.

---

## Item format

Each item uses this block. Goal + AC are the critical fields — they're what lets the operator
decide in-thread whether to execute, spec more deeply, or defer. AC can be skeletal; the operator
will refine them in conversation before execution begins.

```markdown
### [ID] Title
- **Severity:** low | medium | high
- **Effort:** low | medium | high
- **Pickup:** active-agent | cleanup-routine | operator-action
- **Ready:** yes | no
- **Ready-when:** optional machine-checkable repository/review gate
- **Files:** path(s) to touch (omit if not yet known)
- **Status:** OPEN | DONE (PR #N / commit sha)

**Background:** what was observed during the session — concrete and skimmable

**Goal:** one sentence describing the desired end state

**Acceptance criteria:**
- [ ] criterion (can be a skeleton — operator refines in conversation before execution)
- [ ] criterion
- [ ] ...

**Proposed approach:** rough direction or options (optional; omit if unclear)
```

Severity = blast radius if left unfixed.
Effort = engineering cost to fix.
Pickup:
- `active-agent` — worth doing soon, can be done inline
- `cleanup-routine` — fine to batch with the weekly sweep
- `operator-action` — needs an operator decision before any code change

`Ready` = the AC are firm enough that an autonomous worker could execute this item to a verifiable
done with no conversation. **Default `no`.** Flipping to `yes` is a deliberate act — the operator (or
a scoping session with operator sign-off) confirms the AC first. Only `Ready: yes` items are
auto-drain eligible.

`Ready-when` is optional and may appear only when the AC are already firm but execution depends on a
machine-checkable condition in repository or review state, such as a merged PR or a generated file
on the default branch. The drain may verify that condition, flip `Ready` to yes, and record dated
evidence in the same queue-only change. Gates must not depend on credentials, production or
third-party state, trigger state, or an operator decision; `operator-action` items never use them.

---

## Pickup protocol

**Any session start** — run `node scripts/compounding-status.mjs` (or the repo's `compounding-status`
package script; falls back to `ls docs/compounding/` off-repo) and skim OPEN items. Surface them to
the operator: *"I see N OPEN compounding items — [C1: title (severity/effort)], [C2: ...]. Want to
tackle any, or should I just proceed?"* Let the operator direct. For `effort:low` + `severity:low`
items with no operator-decision dependency, you may knock them out silently inline.

**Before executing any OPEN item** — if the AC are skeletal, offer to flesh them out in
conversation first: *"C3's AC are rough — want me to scope it fully before we build?"*

**When done** — set `Status: DONE (PR #N)` in the item. Do not delete the file; it's an audit trail.

**Status currency is continuous, not wrap-up-driven**: flip a status **in the same PR/session as the
change that made it true** — never park it for an end-of-session sweep the operator may never ask
for. Backstop: the drain's STEP 1.5 status-hygiene pass flips any OPEN item whose referenced
PR merged and corrects git-contradicted status prose. State the selector can't verify from git
(external systems, live configs) is updated same-PR by whichever session touches that system.

**Weekly cleanup routine** — full scan of all OPEN items. Execute remaining `effort:low` items.
Summarize `effort:medium` items for the operator. Leave `operator-action` items untouched.
Also review STALE and NEEDS-REVIEW items surfaced by the selector — reclaim or retire them — and
run `/compounding upgrade` so this repo's installed system tracks the canonical templates. Then run
`/compounding-curate` (the context-lifecycle pass): the loop only ever ADDS knowledge, so the
always-on context (AGENTS.md standing practices, this SOP, any "current state" doc) grows unbounded
until it collapses — curate dedups, compresses, promotes stable practices into skills, and retires
stale entries so the context every session pays for stays lean. If product or architecture changed since the
last pass, also reconcile the PRD and technical index. Inspect linked technical topic docs only when evidence
shows they are affected; do not make the whole technical tree always-on.

Before a substantive session closes, every remaining follow-up must be completed, represented by an OPEN
queue item with an owner and acceptance criteria, or identified as a true operator-only action. A loose end
mentioned only in a final message is not durable state.

---

## Validating a fix — held-in + held-out (self-harness discipline)

A self-improvement loop is a **propose → validate → accept** cycle, and validation has TWO halves. A
fix is only *done* when it BOTH resolves the weakness it claims to (**held-in**) AND breaks nothing else
(**held-out**). The daily suite green-check is only the held-out half — a passing suite does **not**
prove the fix addressed the root cause (the item could be "fixed" and still broken).

- **Held-in (the weakness is actually resolved):** a **bug / behavioral** item ships a regression test
  that **fails on the pre-fix code and passes after the fix** — the failing test IS the proof the
  weakness exists and the fix closes it, and it guards against regression forever. Write it FIRST
  (watch it fail on the current code), then fix (watch it pass). This makes a "DONE" flip mean *proven
  resolved*, not *CI happens to be green*. Doc-only, config, and pure-refactor items are exempt (no
  behavior to pin) — say so in the PR.
- **Held-out (nothing else regressed):** the repo's full gate (typecheck + tests — the daily
  green-check) stays green.

### Never reach green by editing the grader (reward-hacking guard)

A self-improvement loop optimizes **whatever signal it is given** — here, "CI is green." So a fix must
**never** reach green by *weakening the very check that judges it*: deleting a test case, loosening an
assertion, relaxing a threshold, or editing an eval that guards the item's own behavior. This is the
**immutable-grader rule**: the thing under test and the test that judges it must not move the same
direction in one change. A drain PR that both changes a behavior AND weakens a grader of that behavior
is a reward-hack smell → it is **never auto-merged**; it stays a draft for human review (drain STEP
4.5). *Adding* the held-in regression test above, or *strengthening* a grader, is always fine.

---

## Item identity & the lock key

Local IDs (`C1`, `C-GPU2`) are NOT globally unique — the same `C1` can exist in multiple session
files. The globally unique **key** is `<file-datestamp>-<id>` (e.g. `20260702-1500-C-LEDGER1`),
derived from the filename. All coordination (claim branches, PR titles) uses the key, never the bare id.

---

## Derived states (never persisted — computed by the selector)

The markdown carries only `OPEN` → `DONE (PR #N)`. Everything in between is DERIVED from GitHub
branch/PR state, so it can't go stale on the default branch:

| State | Meaning |
|---|---|
| `ELIGIBLE` | OPEN + `Ready: yes` + `Pickup ∈ {active-agent, cleanup-routine}` + effort within the configured ceiling + unclaimed. Human-readable mirror of the selector: severity descending, effort ascending, oldest first; the default effort ceiling is `low` (see `compounding-status.mjs`). |
| `IN-PROGRESS` | an open PR references the key — a thread is working it; do not pick it up |
| `CLAIMED` | claim branch `compounding/<key>` exists; PR data unavailable on this surface — treat as in-progress |
| `NEEDS-REVIEW` | a prior PR was closed unmerged (rejected fix) — a human decides whether to retry; never auto-retried |
| `STALE` | open PR idle > 7 days, or an orphan claim branch with no PR — reclaim candidate for the weekly sweep |
| `BLOCKED` | operator-action, `Ready: no`, or effort above the auto ceiling — surfaced, never auto-run |

---

## Auto-drain (bounded scheduled worker)

A routine using the portable `compounding-drain` skill first reconciles
git-verifiable statuses and admissible `Ready-when` gates, then drains up to **three** eligible items
one at a time. Per item it uses the selector's ranking (see `compounding-status.mjs`), claims branch
`compounding/<key>` with an empty commit + draft PR as the atomic mutex, implements to the AC, runs
the green-check, flips the item to `DONE (PR #N)` in the same diff, and:

- diff touches ONLY `docs/compounding/**` → marks the PR ready and the `auto-merge-journal`
  workflow lands it;
- anything else (code, skills, workflows) → leaves a **draft PR** for human merge.

After each item reaches its review state, the worker returns to a fresh default branch and re-runs
the selector. It stops when the queue is dry, three items have been handled, or safe progress needs
an operator. The repository owns cadence: align runs to when eligibility changes; twice daily may be
appropriate for a repository with two meaningful eligibility windows. Scheduling remains a provider
adapter concern rather than part of this portable workflow.

Zero ELIGIBLE items ⇒ clean no-op. The worker never merges code, never touches credentials/secrets
or money-moving/state-mutating systems, never force-pushes, never deletes branches, never pushes the
default branch directly.

---

## Upstreaming — compounding the compounding system

Improvements to the SYSTEM itself (this SOP's rules, selector behavior, the drain protocol, the
workflow) are not repo-local: file them as a queue item with an extra line after `Pickup:`:

```markdown
- **Upstream:** claude_tools
```

**Scope — what actually qualifies (VERIFY before you tag).** `Upstream: claude_tools` is ONLY for
components of the compounding system that live in the canonical AI Tools repository: the portable
`maintain-technical-design` skill and asset, this template pack, the `compounding-*` skills, the selector
(`compounding-status.mjs`), the drain/curate protocol, and `auto-merge-journal.yml`. A repo-local tool that
merely gets *used* during compounding work
— a project's own research harness, build script, or eval — is **NOT** a compounding-system component:
fix it in its own repo and do **not** tag it `Upstream: claude_tools`. Before you add the tag (or act
on one you find), confirm the target file exists under `commands/compounding-templates/` or
`skills/maintain-technical-design/` — **do not infer a canonical claude_tools copy from the tag itself.**
*(War-story, 2026-07-08: a trading repo's
`thesis-research.js` harness fix was tagged `Upstream: claude_tools`; a later session added the
claude_tools repo and hunted for a copy that never existed — the harness only ever lived in that one
repo. The mis-tag cost a round-trip; the verify-first rule kills it.)*

Executing an upstream item means PRing `github.com/MSilb7/claude_tools`
(`commands/compounding-templates/` + a `VERSION` bump), after which **every** repo's next
`/compounding upgrade` inherits the improvement. Never fork the system silently in one repo — that
recreates the drift this design exists to kill.

---

## Wiring

This SOP is referenced from the repo's agent instructions (installed by `/compounding setup`), which
is how both headless routine runs and interactive sessions see the convention. The technical-design
pointer lives in the canonical shared agent file when one exists and delegates procedure to the
portable skill instead of expanding always-on context.
