---
name: live-draft-companion
description: Run the live ESPN draft companion for The Brady Bunch when the user says "run now", "my pick", "on the clock", or asks who to draft next.
---

# Live Draft Companion

Return a current, clock-safe top-10 recommendation table for league profile `the_brady_bunch` in
season 2026.

## Live run

Immediately refresh and rank with one command from the repository root:

```bash
PYTHONPATH=src /opt/homebrew/bin/python3 -m fantasy_assistant.cli draft-board \
  --league the_brady_bunch --season 2026 --limit 10 --refresh
```

This command already removes every keeper and completed pick from availability, counts each keeper
or selection toward its team's positional holdings, skips keeper-reserved slots when measuring the
next decision horizon, and incorporates all teams' current positional needs into opponent demand.
Do not recreate those calculations from raw ESPN dictionaries.

Lead with the recommended selection, then reproduce the top-10 table. State whether the user is on
the clock, the current pick, their next pick, and the snapshot timestamp. All 0–100 ratings are
higher-is-better except that `Gone next` means greater risk the player will be unavailable at the
user's following decision. Describe opponent demand and gone-next ratings as explainable heuristics,
not calibrated certainty.

For draft-clock speed, do not browse news or refresh the full league/player pool before the normal
run. Refresh player evidence only if the user asks about breaking news/injury context or the command
reveals missing/stale baseline data.

If the live refresh fails, run the same command without `--refresh` once and clearly label the
snapshot timestamp as stale. Do not spend the pick clock on repeated network retries. Never submit a
selection to ESPN; the user makes the final pick.
