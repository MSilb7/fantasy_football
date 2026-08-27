# Payout calculator

This directory preserves the original ESPN payout workflow as a self-contained application.
The notebooks retain their year-specific calculation logic; the 2025 notebook is the current
reference implementation.

## Run

From the repository root:

```bash
python -m pip install -e '.[payouts]'
jupyter notebook apps/payouts/notebooks/pull_scores_2025.ipynb
```

The notebooks read ESPN credentials from the repository-root `.env` and write generated files to
`apps/payouts/outputs/`. Generated reports are local-only and ignored by git.

## Preserved versions

- `notebooks/pull_scores_2023.ipynb` — original endpoint and weekly-high CSV.
- `notebooks/pull_scores_2024.ipynb` — updated ESPN read endpoint.
- `notebooks/pull_scores_2025.ipynb` — current multi-tab payout workbook.

The notebooks remain a separate presentation application, while financial allocation is shared
through `src/fantasy_assistant/payouts.py`. The 2025 notebook imports that module so payout rules are
tested once rather than copied into notebook cells.

## Funding guarantee

Every payout comes from the total pot of team buy-ins. Weekly highs are removed first, the fixed
third-place award is removed next, and first and second split the remaining placement pool. The
workbook's Parameters tab verifies that weekly highs plus all three placement payouts equal the
total pot.

Reports generated before commit `d2c0546` are not rewritten automatically. Re-run the 2025 notebook
to replace a prior local workbook with the corrected allocation.
