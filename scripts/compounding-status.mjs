// compounding-system: v8 — installed from claude_tools; do not hand-edit; run /compounding upgrade
//
// Machine-readable compounding-queue status. Parses docs/compounding/*.md items and derives each
// item's coordination state from GitHub branch/PR refs: git ls-remote on compounding/* claim
// branches is the load-bearing lock (works everywhere git works); `gh pr list` only upgrades
// reporting fidelity (IN-PROGRESS vs NEEDS-REVIEW) — when absent we run degraded and say so.
//
// Zero dependencies; runs under node >=18 or bun. Behavior contract shared with the reference
// implementation (investment-agent src/server/engine/compounding/queue.ts) — improvements to either
// are Upstream: claude_tools items (see SOP.md § Upstreaming).
//
// Usage:
//   node scripts/compounding-status.mjs           # human report (stderr) + summary line (stdout)
//   node scripts/compounding-status.mjs --json    # {generatedAt, degraded, maxEffort, items, eligible}
//   COMPOUNDING_MAX_EFFORT=low|medium|high        # auto-eligibility effort ceiling (default low)

import { readdirSync, readFileSync, realpathSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { pathToFileURL } from "node:url";

/** "2026-07-02-1500.md" → "20260702-1500" (date loses its dashes; the time keeps its separator). */
export function datestampFromFileName(fileName) {
  const base = fileName.replace(/\.md$/, "");
  const m = base.match(/^(\d{4})-(\d{2})-(\d{2})-(\d{4})$/);
  if (!m) return base.replace(/-/g, "");
  return `${m[1]}${m[2]}${m[3]}-${m[4]}`;
}

/** `### [C-GPU1] Title`, `### C1 Title`, `## C-SIG1 — Title` — h2/h3, optional brackets/em-dash. */
const HEADER_RE = /^#{2,3}\s+\[?(C-?[A-Z]*\d+[A-Z0-9]*)\]?\s*(?:[—–-]\s*)?(.*)$/;

function normLevel(raw) {
  const v = raw.trim().toLowerCase();
  if (v.startsWith("low")) return "low";
  if (v.startsWith("med")) return "medium";
  if (v.startsWith("high")) return "high";
  return "unknown";
}

function normPickup(raw) {
  const v = raw.trim().toLowerCase();
  if (v.startsWith("active-agent")) return "active-agent";
  if (v.startsWith("cleanup-routine")) return "cleanup-routine";
  if (v.startsWith("operator-action")) return "operator-action";
  return "unknown";
}

export function parseCompoundingFile(fileName, content) {
  const stamp = datestampFromFileName(fileName);
  const lines = content.split("\n");
  const items = [];
  let cur = null;

  const field = (line, name) => {
    const m = line.match(new RegExp(`^\\s*-\\s+\\*\\*${name}:\\*\\*\\s*(.+)$`, "i"));
    return m ? m[1].trim() : null;
  };

  for (const line of lines) {
    const h = line.match(HEADER_RE);
    if (h) {
      cur = {
        key: `${stamp}-${h[1]}`,
        id: h[1],
        title: h[2].replace(/~~/g, "").trim(),
        file: fileName,
        severity: "unknown",
        effort: "unknown",
        pickup: "unknown",
        ready: false,
        readyWhen: null,
        statusRaw: "",
        done: false,
        goal: null,
        acCount: 0,
      };
      items.push(cur);
      continue;
    }
    if (!cur) continue;

    // Combined legacy form: `- **Severity / effort:** MED / MED`
    const combined = line.match(/^\s*-\s+\*\*Severity\s*\/\s*effort:\*\*\s*(\S+)\s*\/\s*(\S+)/i);
    if (combined) {
      cur.severity = normLevel(combined[1]);
      cur.effort = normLevel(combined[2]);
      continue;
    }
    const sev = field(line, "Severity");
    if (sev !== null && cur.severity === "unknown") { cur.severity = normLevel(sev); continue; }
    const eff = field(line, "Effort");
    if (eff !== null && cur.effort === "unknown") { cur.effort = normLevel(eff); continue; }
    const pick = field(line, "Pickup");
    if (pick !== null) { cur.pickup = normPickup(pick); continue; }
    const ready = field(line, "Ready");
    if (ready !== null) { cur.ready = ready.trim().toLowerCase().startsWith("yes"); continue; }
    const readyWhen = field(line, "Ready-when");
    if (readyWhen !== null) { cur.readyWhen = readyWhen; continue; }
    const status = field(line, "Status");
    if (status !== null) {
      cur.statusRaw = status;
      // Tolerate leading markdown emphasis/quotes ("**DONE**", "_RESOLVED_", '"CLOSED"') — a bolded
      // status keyword must still register as terminal (else a done item silently shows as open).
      cur.done = /^[\s*_"'`]*(DONE|RESOLVED|CLOSED)/i.test(status.trim());
      continue;
    }
    const goal = line.match(/^\*\*Goal:\*\*\s*(.+)$/);
    if (goal) { cur.goal = goal[1].trim(); continue; }
    if (/^\s*-\s+\[[ x]\]/i.test(line)) cur.acCount++;
  }
  return items;
}

export function claimBranch(key) {
  return `compounding/${key}`;
}

const AUTO_PICKUPS = ["active-agent", "cleanup-routine"];
const EFFORT_RANK = { low: 1, medium: 2, high: 3, unknown: 99 };
const SEVERITY_RANK = { low: 1, medium: 2, high: 3, unknown: 0 };

function prAgeDays(pr, now) {
  if (!pr.updatedAt) return 0;
  return (now.getTime() - new Date(pr.updatedAt).getTime()) / 86_400_000;
}

export function classifyQueue(items, refs, maxEffort = "low") {
  const staleDays = refs.staleDays ?? 7;
  return items.map((it) => {
    const branch = claimBranch(it.key);
    const branchExists = refs.branches.includes(branch);
    const matching = refs.prs
      ? refs.prs.filter((p) => p.headRef === branch || p.title.includes(it.key))
      : null;

    const to = (state, reason) => ({ ...it, state, reason });

    if (it.done) return to("DONE", it.statusRaw);
    const openPr = matching?.find((p) => p.state === "open");
    if (openPr) {
      return prAgeDays(openPr, refs.now) > staleDays
        ? to("STALE", `open PR idle > ${staleDays}d — reclaim candidate`)
        : to("IN-PROGRESS", `open PR on ${openPr.headRef}`);
    }
    const closedPr = matching?.find((p) => p.state === "closed" || p.state === "merged");
    if (closedPr) return to("NEEDS-REVIEW", "prior PR closed while item still OPEN — human decides retry");
    if (branchExists && matching === null) return to("CLAIMED", "claim branch exists; PR data unavailable");
    if (branchExists) return to("STALE", "orphan claim branch (no PR) — reclaim candidate");
    if (!AUTO_PICKUPS.includes(it.pickup)) return to("BLOCKED", `pickup: ${it.pickup}`);
    if (!it.ready) return to("BLOCKED", "Ready: no — AC not firm enough to auto-execute");
    if (EFFORT_RANK[it.effort] > EFFORT_RANK[maxEffort]) return to("BLOCKED", `effort ${it.effort} > ceiling ${maxEffort}`);
    return to("ELIGIBLE", "open, ready, unclaimed");
  });
}

export function rankEligible(classified) {
  return classified
    .filter((c) => c.state === "ELIGIBLE")
    .sort(
      (a, b) =>
        SEVERITY_RANK[b.severity] - SEVERITY_RANK[a.severity] ||
        EFFORT_RANK[a.effort] - EFFORT_RANK[b.effort] ||
        a.key.localeCompare(b.key),
    );
}

// ---------------------------------------------------------------------------
// CLI

const DIR = "docs/compounding";

function shell(cmd, args) {
  try {
    const p = spawnSync(cmd, args, { encoding: "utf8" });
    return p.status === 0 ? p.stdout : null;
  } catch {
    return null;
  }
}

function remoteClaimBranches() {
  const out = shell("git", ["ls-remote", "origin", "refs/heads/compounding/*"]);
  if (out === null) {
    console.error("  ⚠ git ls-remote failed — claim-branch lock UNAVAILABLE; treating nothing as claimed.");
    return [];
  }
  return out
    .split("\n")
    .map((l) => l.split("\t")[1])
    .filter(Boolean)
    .map((ref) => ref.replace("refs/heads/", ""));
}

function listPrs() {
  const out = shell("gh", [
    "pr", "list", "--state", "all", "--limit", "200",
    "--json", "headRefName,title,state,updatedAt,mergedAt",
  ]);
  if (out === null) return null;
  try {
    return JSON.parse(out).map((r) => ({
      headRef: r.headRefName,
      title: r.title,
      state: r.state === "OPEN" ? "open" : r.mergedAt ? "merged" : "closed",
      updatedAt: r.updatedAt ?? null,
    }));
  } catch {
    return null;
  }
}

function main() {
  const json = process.argv.includes("--json");
  const maxEffort = process.env.COMPOUNDING_MAX_EFFORT ?? "low";

  let files;
  try {
    files = readdirSync(DIR).filter((f) => /^\d{4}-\d{2}-\d{2}-\d{4}\.md$/.test(f));
  } catch {
    console.error(`  ⚠ ${DIR}/ not found — run from the repo root (or bootstrap with /compounding setup).`);
    process.exit(1);
  }
  const items = files.flatMap((f) => parseCompoundingFile(f, readFileSync(join(DIR, f), "utf8")));

  const prs = listPrs();
  const refs = { branches: remoteClaimBranches(), prs, now: new Date() };
  const classified = classifyQueue(items, refs, maxEffort);
  const eligible = rankEligible(classified);
  const degraded = prs === null;

  if (degraded) console.error("  ⚠ gh unavailable — degraded mode (branch lock only; no NEEDS-REVIEW detection).");
  for (const state of ["ELIGIBLE", "IN-PROGRESS", "CLAIMED", "NEEDS-REVIEW", "STALE", "BLOCKED", "DONE"]) {
    const group = classified.filter((c) => c.state === state);
    if (!group.length) continue;
    console.error(`  ${state} (${group.length}):`);
    for (const c of group) console.error(`    ${c.key} [sev:${c.severity}/eff:${c.effort}] ${c.title} — ${c.reason}`);
  }

  if (json) {
    console.log(JSON.stringify({ generatedAt: refs.now.toISOString(), degraded, maxEffort, items: classified, eligible }, null, 2));
  } else {
    console.log(
      `eligible=${eligible.length}` +
      ` in-progress=${classified.filter((c) => c.state === "IN-PROGRESS" || c.state === "CLAIMED").length}` +
      ` blocked=${classified.filter((c) => c.state === "BLOCKED").length}` +
      ` done=${classified.filter((c) => c.state === "DONE").length}` +
      ` total=${classified.length}${degraded ? " (degraded)" : ""}`,
    );
  }
}

// Direct-execution check must survive symlinked installs (node resolves import.meta.url to the
// realpath, but argv[1] stays the symlink) — compare realpaths on both sides.
const isDirectRun = (() => {
  if (!process.argv[1]) return false;
  try {
    return pathToFileURL(realpathSync(process.argv[1])).href === import.meta.url;
  } catch {
    return false;
  }
})();
if (isDirectRun) main();
