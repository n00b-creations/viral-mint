# ViralMint

ViralMint is a standalone cryptocurrency market-attention research project. It collects public market-pair data, computes transparent research signals, and helps investigate whether an asset's observable market activity is changing.

> **Research only.** Scores are heuristic indicators, not predictions or financial advice. Cryptocurrency assets can lose all value. ViralMint does not execute trades, connect to wallets, or manage funds.

## Project status

**Initial research MVP scaffold.** The repository now contains a Python library, a command-line token query, an explainable market-activity score, offline tests, and a GitHub Actions test workflow. This is not yet a production monitoring service and does not measure social attention.

## Initial capabilities

- Fetch public token-pair data from the Dexscreener API.
- Normalize market fields and handle missing or malformed values conservatively.
- Calculate a transparent 0–100 **market-activity score** from liquidity, one-hour transaction activity, one-hour volume, and short-window price movement.
- Return score components and data-quality warnings.
- Run offline unit tests with mocked HTTP responses.
- Export a token's pair summary as JSON to standard output.

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

Query a token address on a supported Dexscreener chain:

```bash
viral-mint token <TOKEN_ADDRESS> --chain solana
```

The CLI prints JSON containing pair metadata, observed market fields, score components, and warnings. Use a real address and the appropriate chain identifier.

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

A token can have multiple pools. Evaluate pool liquidity, pool age, and data quality before drawing conclusions.

## What the score means

The score is a heuristic measure of **observable market activity**, not virality. Market data alone cannot verify social momentum, news catalysts, token legitimacy, or future returns. The current score measures the magnitude of one-hour price movement, not whether that movement is positive; a sharp drop can therefore contribute to the movement component. It is not a token-safety score.

Weights and saturation thresholds are initial heuristics, not empirically calibrated predictors. Missing components are omitted and remaining weights are renormalized; the output includes warnings when coverage is partial. Compare scores only when the underlying data and observation windows are reasonably comparable.

## Data handling and limitations

- Uses public market-pair data from Dexscreener; API fields, limits, and availability can change.
- Network calls have a timeout and raise explicit errors for HTTP or malformed responses.
- No fabricated social signals, news mentions, holder counts, or sentiment metrics are generated.
- This version does not screen for honeypots, contract exploits, wash trading, insider concentration, or liquidity locks.
- No automated trading, wallet connection, or order execution is included.
- Do not put private keys, exchange credentials, or wallet seed phrases in this project.

## Development and CI

```bash
python -m pip install -e ".[dev]"
pytest
```

GitHub Actions is configured to run the test suite on pushes to `main`, pull requests, and manual dispatch. A workflow configuration is not proof that a run has passed; check the repository's Actions tab for actual run results.

See [CHANGELOG.md](CHANGELOG.md) for milestone history and [SECURITY.md](SECURITY.md) for responsible reporting.

## Roadmap

1. **Foundation (in progress):** validated models, Dexscreener client, explainable market-activity score, CLI, offline tests, and CI.
2. Add retries, rate-limit-aware backoff, caching, and JSON/CSV export options.
3. Store historical snapshots and calculate time-series acceleration rather than relying only on a single snapshot.
4. Add optional, source-attributed social/news adapters with provenance and freshness metadata.
5. Backtest and calibrate scores against historical outcomes, accounting for survivorship bias and data-quality limitations.
6. Add a dashboard after the data and scoring pipeline is reproducible.

Roadmap items beyond the current code are planned, not implemented.
