# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This repository calculates fantasy football payouts for an ESPN Fantasy Football league. It pulls league data from ESPN's API and generates auditable payout reports based on playoff results and weekly high scores.

## Running the Notebooks

**Quick start:**
```bash
# Run the latest notebook (recommended)
jupyter notebook pull_scores_2025.ipynb
```

**Dependencies:**
- pandas
- requests
- python-dotenv

Install if needed:
```bash
pip install pandas requests python-dotenv
```

## ESPN API Authentication

The notebooks require ESPN Fantasy Football credentials in `.env`:

```
league_id = 629128
espn_s2 = <your_espn_s2_cookie>
swid = <your_swid_cookie>
```

**To find these values:**
1. Log into ESPN Fantasy Football in a browser
2. Open browser dev tools → Application/Storage → Cookies
3. Find `espn_s2` and `SWID` cookie values
4. Copy league ID from URL: `fantasy.espn.com/football/league?leagueId=XXXXXX`

The `.env` file is gitignored to prevent credential leaks.

## Architecture

**Notebook Evolution:**
- `pull_scores_2023.ipynb` - Original version using older ESPN API endpoint
- `pull_scores_2024.ipynb` - Updated to use `lm-api-reads.fantasy.espn.com`
- `pull_scores_2025.ipynb` - **Current template** - fully optimized, automated playoff detection

**Always use pull_scores_2025.ipynb as the reference** - it has:
- Single optimized API call (reduced from 3-4 calls in earlier versions)
- Automatic extraction of league parameters (teams, weeks, playoff results)
- Optimized pandas operations (idxmax, merge instead of loops)
- Manual input only for financial decisions ESPN doesn't track

**API Structure:**

The ESPN Fantasy API endpoint:
```
https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/segments/0/leagues/{league_id}
```

Single request fetches all needed data using multiple views:
```python
params = {"view": ["mTeam", "mMatchup", "mMatchupScore", "mStandings"]}
headers = {
    "X-Fantasy-Filter": json.dumps({
        "schedule": {"filterMatchupPeriodIds": {"value": list(range(1, 18))}}
    })
}
```

**Key API Response Fields:**
- `teams[]` - Team names, owners, playoff rankings (rankCalculatedFinal, rankFinal, playoffSeed)
- `members[]` - Owner first/last names mapped by ID
- `schedule[]` - Weekly matchup scores (home/away team scores by matchupPeriodId)
- `settings.scheduleSettings` - Regular season length (matchupPeriodCount)

**Payout Logic:**

1. **Automatic from API:**
   - Number of teams
   - Regular season weeks
   - Playoff results (1st, 2nd, 3rd place) via rankCalculatedFinal fallback chain
   - All weekly scores

2. **Manual configuration (Cell #2):**
   - Buy-in amount
   - Weekly highs share percentage
   - Winner split percentages
   - Third place fixed payout

3. **Calculation:**
   - Total pot = teams × buy-in
   - Weekly highs pot = total × weekly_highs_share
   - Winners pot = total - weekly_highs_pot - third_place_payout
   - First/second split winners pot by configured percentages
   - Weekly highs distributed evenly across regular season weeks

**Output Structure:**

The notebook exports a multi-tab Excel file to `outputs/fantasy_football_payouts_{year}.xlsx` with:
- **Tab 1: Final Payouts** - Per-owner payout breakdown (main summary)
- **Tab 2: Weekly Highs** - Weekly high score winners
- **Tab 3: All Scores** - Complete score data for all teams/weeks
- **Tab 4: Parameters** - League configuration and audit trail

This XLSX file can be uploaded directly to Google Sheets for league transparency.

**Dependencies:** Requires `openpyxl` for Excel export (auto-installs if missing).

## Making Changes

**Creating a new year's notebook:**
1. Copy `pull_scores_2025.ipynb` to `pull_scores_{new_year}.ipynb`
2. Update only Cell #2 if payout structure changed
3. Run all cells - playoff detection is automatic once ESPN finalizes standings

**If playoffs aren't final yet:**
- Notebook will auto-detect and fall back to manual entry cell
- Edit team names in the manual entry cell (uses team names like "BEC Michael", not owner names)

**Key constraint:**
User input cells MUST be at the top of the notebook (Cells #2-3). This was a specific user requirement after initial confusion.
