# Fantasy Football Payout Calculator

Automated payout calculator for ESPN Fantasy Football leagues. Fetches league data from ESPN's API and generates auditable payout reports based on playoff results and weekly high scores.

## Features

- **Automatic Data Fetching**: Pulls all league data directly from ESPN API
  - Team information and owner names
  - Weekly scores for entire season
  - Playoff results (1st, 2nd, 3rd place)
  - League settings (number of teams, regular season length)

- **Configurable Payout Structure**:
  - Set your own buy-in amount
  - Configure percentage splits for weekly highs and playoff winners
  - Fixed third-place payout

- **Auditable Excel Export**: Single multi-tab spreadsheet with:
  - Final payout summary
  - Weekly high scores
  - All scores by week
  - League parameters for transparency

## Prerequisites

- Python 3.7+
- Jupyter Notebook
- ESPN Fantasy Football league access

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd fantasy_football
```

2. Install required packages:
```bash
pip install pandas requests python-dotenv openpyxl jupyter
```

## Setup

### 1. Get ESPN API Credentials

You need three values from your ESPN Fantasy Football account:

1. **League ID**: Found in your league URL
   - URL format: `fantasy.espn.com/football/league?leagueId=XXXXXX`
   - Copy the number after `leagueId=`

2. **ESPN S2 Cookie**: From your browser
   - Log into ESPN Fantasy Football
   - Open browser Developer Tools (F12)
   - Go to Application → Cookies → `espn.com`
   - Find and copy the `espn_s2` cookie value

3. **SWID Cookie**: From the same location
   - In the same Cookies section
   - Find and copy the `SWID` cookie value (includes curly braces)

### 2. Create Environment File

Create a `.env` file in the repository root with your credentials:

```
league_id = YOUR_LEAGUE_ID
espn_s2 = YOUR_ESPN_S2_COOKIE_VALUE
swid = YOUR_SWID_COOKIE_VALUE
```

**Important**: The `.env` file is gitignored to protect your credentials.

## Usage

1. Open the notebook:
```bash
jupyter notebook pull_scores_2025.ipynb
```

2. **Configure payout structure** (Cell #2):
   - Update `BUY_IN` amount
   - Set `SHARE_FOR_WEEKLY_HIGHS` percentage
   - Configure winner split percentages
   - Set third place payout

3. **Run all cells** (Cell → Run All)

4. The notebook will:
   - Fetch all league data from ESPN
   - Automatically detect playoff winners (if playoffs are complete)
   - Calculate weekly high scores
   - Calculate final payouts
   - Export multi-tab Excel file to `outputs/`

5. **Manual entry** (only if needed):
   - If playoffs aren't complete, enter team names manually in Cell #12
   - Use team names (e.g., "BEC Michael") not owner names

## Output

The notebook creates `outputs/fantasy_football_payouts_2025.xlsx` with four tabs:

1. **Final Payouts** - Complete payout breakdown by owner
2. **Weekly Highs** - Weekly high score winners
3. **All Scores** - All team scores by week
4. **Parameters** - League configuration and audit trail

Upload this file directly to Google Sheets to share with your league.

## Year-to-Year Usage

To create a notebook for a new season:

1. Copy `pull_scores_2025.ipynb` to `pull_scores_YYYY.ipynb`
2. Update Cell #2 if your payout structure changed
3. Run the notebook - everything else is automatic

The 2025 notebook is the current optimized template. Older notebooks (2023, 2024) are kept for reference.

## How It Works

**Payout Calculation:**
1. Total pot = Number of teams × Buy-in
2. Weekly highs pot = Total × Weekly highs percentage
3. Winners pot = Total - Weekly highs pot - Third place payout
4. First/second place split the winners pot by configured percentages
5. Weekly high pot distributed evenly across regular season weeks

**API Optimization:**
- Single API call fetches all required data (teams, scores, standings, settings)
- Optimized pandas operations for fast processing
- Automatic fallback to manual entry if needed

## Troubleshooting

**Import cell is slow:**
- This is normal - pandas takes 1-3 seconds to import on first run
- Subsequent cells will be much faster

**"Playoffs incomplete" message:**
- ESPN hasn't finalized playoff rankings yet
- Use the manual entry cell to input team names
- Re-run after ESPN updates standings for automatic detection

**API authentication errors:**
- Verify your `.env` file credentials are correct
- ESPN cookies may expire - get fresh values from your browser
- Make sure you're logged into ESPN Fantasy Football

## Questions?

This notebook is designed for a 12-team league with configurable payout structure. All league parameters are pulled automatically from ESPN's API - you only configure the financial decisions that ESPN doesn't track.
