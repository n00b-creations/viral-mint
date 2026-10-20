# ViralMint

ViralMint is a standalone cryptocurrency market-attention research project. It collects public market-pair data, computes transparent research signals, and helps investigate whether an asset's observable market activity is changing.

> **Research only.** Scores are heuristic indicators, not predictions or financial advice. Cryptocurrency assets can lose all value. ViralMint does not execute trades, connect to wallets, or manage funds.

## Project status

**Initial scaffold.** The first milestone provides a small Python library for retrieving Dexscreener pair data and calculating explainable attention scores. It is not yet a production monitoring service and does not claim to measure social attention unless a configured, real source supplies that data.

## Initial capabilities

- Fetch public token-pair data from the Dexscreener API.
- Normalize market fields and handle missing values conservatively.
- Calculate a transparent 0–100 **market-activity score** from liquidity, transaction activity, volume, and short-window price movement.
- Return score components and data-quality warnings so a score can be inspected rather than treated as a black box.
- Test scoring behavior without network access.
- Keep API credentials out of source code; the initial Dexscreener endpoints used here are public.

## What the score means

The initial score is a heuristic measure of **observable market activity**, not virality. Market data alone cannot verify social momentum, news catalysts, token legitimacy, or future returns. Missing fields are not silently interpreted as evidence of strength. Scores should be compared only when the underlying data and observation windows are reasonably comparable.

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

Run a simple query:

```bash
viral-mint token <TOKEN_ADDRESS> --chain solana
```

The CLI will be added in a subsequent milestone; until then, use the library directly or wait for the CLI implementation.

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

Use a real token address for the chain you specify. A token can have multiple pools; evaluate pool liquidity and pair age before drawing conclusions.

## Data handling and limitations

- Uses public market-pair data from Dexscreener; API fields, limits, and availability can change.
- Network calls have timeouts and raise explicit errors for HTTP or malformed responses.
- No fabricated social signals, news mentions, holder counts, or sentiment metrics are generated.
- This initial version does not screen for honeypots, contract exploits, wash trading, insider concentration, or liquidity locks.
- No automated trading, wallet connection, or order execution is included.
- Do not put private keys, exchange credentials, or wallet seed phrases in this project.

## Development

```bash
python -m pip install -e ".[dev]"
pytest
```

See [CHANGELOG.md](CHANGELOG.md) for milestone history. See [SECURITY.md](SECURITY.md) for responsible reporting.

## Roadmap

1. **Foundation:** validated models, Dexscreener client, explainable market-activity score, offline tests.
2. CLI and JSON/CSV exports; retries, rate-limit handling, and caching.
3. Historical snapshots and time-series deltas to distinguish acceleration from absolute activity.
4. Optional, source-attributed social/news adapters with provenance and freshness metadata.
5. Backtesting and score calibration against historical outcomes, with survivorship-bias and data-quality checks.
6. Dashboard only after the data and scoring pipeline are testable and reproducible.

All roadmap items beyond the current scaffold are planned, not implemented.
