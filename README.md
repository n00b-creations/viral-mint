# ViralMint

ViralMint is a standalone cryptocurrency market-attention research project. It collects public market-pair data, computes transparent research signals, and tracks observations over time so researchers can inspect changes in observable activity.

> **Research only.** Scores are heuristic indicators, not predictions or financial advice. Cryptocurrency assets can lose all value. ViralMint does not execute trades, connect to wallets, or manage funds.

## Project status

**Research MVP foundation.** The repository includes a Python library, CLI, Dexscreener public market-data client, explainable market-activity scoring, local SQLite snapshots, historical delta/rate calculations, tests, and a GitHub Actions test workflow. It is not yet a production monitoring service and does not measure social attention.

## Capabilities

- Fetch public token-pair data from the Dexscreener API.
- Normalize market fields and handle malformed values conservatively.
- Calculate a transparent 0–100 market-activity score using liquidity, one-hour volume, transaction activity, and one-hour price-movement magnitude.
- Save timestamped observations to a local SQLite database.
- Compare recent observations and calculate descriptive hourly changes.
- Estimate a change in hourly rate (“acceleration”) for volume and score when at least three valid observations are available.
- Emit JSON with score components, data-quality warnings, and history.
- Run offline tests with mocked HTTP responses.

## Quick start

Requires Python 3.11 or newer.

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell:
# .venv\Scripts\Activate.ps1

python -m pip install -e ".[dev]"
pytest
```

### 1. Inspect a token

```bash
viral-mint token YOUR_TOKEN_ADDRESS --chain solana
```

### 2. Save an observation

```bash
viral-mint snapshot YOUR_TOKEN_ADDRESS --chain solana
```

This fetches current pairs and saves one observation per returned pair in `data/viral_mint.sqlite3`. The database is local and ignored by Git. Re-run the command later to build a time series. A single observation cannot establish a trend.

You can specify another local database path with `--db`.

### 3. Compare historical observations

Copy the exact `pair_address` from the snapshot output, then run:

```bash
viral-mint history YOUR_TOKEN_ADDRESS --chain solana --pair YOUR_PAIR_ADDRESS
```

The command returns stored observations, the latest pairwise changes, elapsed time, hourly rates, and—when at least three observations exist—a descriptive change in hourly rate. Use the same token, chain, pair address, and database for consistent comparisons.

Use `--limit 50` to load up to 50 recent observations. Supported range is 1–1000.

## Library example

```python
import asyncio
from viral_mint.dexscreener import DexscreenerClient
from viral_mint.scoring import score_pair

async def main():
    async with DexscreenerClient() as client:
        pairs = await client.get_token_pairs("solana", "TOKEN_ADDRESS")
    for pair in pairs:
        result = score_pair(pair)
        print(pair.base_token.symbol, result.score, result.components, result.warnings)

asyncio.run(main())
```

## Interpreting scores and historical changes

The score is a heuristic measure of **observable market activity**, not virality, token safety, or future returns. The price-movement component uses absolute magnitude, so a sharp price drop can increase that component. Transaction counts do not identify unique traders or establish organic demand.

Weights and thresholds are initial heuristics, not empirically calibrated predictors. Missing components are omitted, remaining weights are renormalized, and warnings disclose partial coverage.

Historical comparisons are descriptive. Dexscreener's rolling-window volume and transaction metrics can overlap between snapshots; a change in the one-hour volume field is **not** the exact amount traded since the previous snapshot. Acceleration depends on the spacing and quality of saved observations and should not be treated as a predictive signal. Irregular or non-increasing timestamps can make hourly rates unavailable.

## Data handling and limitations

- Uses public market-pair data from Dexscreener; API fields, rate limits, and availability can change.
- Network calls have a timeout and raise explicit errors for HTTP or malformed responses.
- No fabricated social signals, news mentions, holder counts, or sentiment metrics are generated.
- No token-risk, honeypot, contract exploit, wash-trading, insider concentration, or liquidity-lock screening is implemented.
- No automated trading, wallet connection, or order execution is included.
- Do not put private keys, exchange credentials, or wallet seed phrases in this project.
- Local SQLite history is not synced or backed up automatically.

## Development and CI

```bash
python -m pip install -e ".[dev]"
pytest
```

GitHub Actions is configured to run the test suite on pushes to `main`, pull requests, and manual dispatch. Verify the Actions tab for actual run results; workflow configuration alone is not proof of a passing run.

See [CHANGELOG.md](CHANGELOG.md) and [SECURITY.md](SECURITY.md).

## Roadmap

1. **Foundation:** market client, explainable score, CLI, SQLite snapshots, historical deltas, offline tests, and CI.
2. Add rate-limit-aware retry/backoff, robust caching, and CSV export.
3. Add explicit observation schedules and snapshot freshness/data-quality reporting.
4. Add optional, source-attributed social/news adapters with provenance, freshness, and coverage metadata.
5. Backtest and calibrate signals against historical outcomes, accounting for survivorship bias and data-quality limitations.
6. Build a dashboard after the data and scoring pipeline is reproducible.

Roadmap items beyond the implemented code are planned, not implemented.
