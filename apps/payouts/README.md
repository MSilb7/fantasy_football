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

The notebooks are intentionally kept separate from `src/fantasy_assistant/`. A future payout
refactor should add regression fixtures first, then move shared ESPN and calculation behavior into
the package without changing historical results.

## Known issue

The 2025 notebook's winner pool currently does not subtract the fixed third-place payout before
splitting first and second place. Its printed total therefore exceeds the pot by that fixed amount.
This was preserved during the folder move and is tracked in `docs/compounding/2026-08-27-1154.md`.
