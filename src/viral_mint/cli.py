"""Command-line entry point for one-token market research."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from viral_mint.dexscreener import DexscreenerClient, DexscreenerError
from viral_mint.scoring import score_pair


async def _token_report(chain: str, address: str) -> int:
    async with DexscreenerClient() as client:
        pairs = await client.get_token_pairs(chain, address)
    report = []
    for pair in pairs:
        score = score_pair(pair)
        report.append({
            "chain_id": pair.chain_id,
            "pair_address": pair.pair_address,
            "dex_id": pair.dex_id,
            "url": pair.url,
            "token": {"name": pair.base_token.name, "symbol": pair.base_token.symbol, "address": pair.base_token.address},
            "price_usd": pair.price_usd,
            "liquidity_usd": pair.liquidity_usd,
            "volume_h1_usd": pair.volume_h1_usd,
            "volume_h24_usd": pair.volume_h24_usd,
            "buys_h1": pair.buys_h1,
            "sells_h1": pair.sells_h1,
            "price_change_h1_pct": pair.price_change_h1_pct,
            "market_activity_score": score.score,
            "score_components": score.components,
            "warnings": list(score.warnings),
        })
    print(json.dumps({"chain": chain, "token_address": address, "pair_count": len(report), "pairs": report}, indent=2))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="viral-mint", description="Research public market activity for a token.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    token_parser = subparsers.add_parser("token", help="Fetch pair data for a token address.")
    token_parser.add_argument("token_address")
    token_parser.add_argument("--chain", required=True, help="Dexscreener chain identifier, e.g. solana or ethereum.")
    args = parser.parse_args()
    try:
        code = asyncio.run(_token_report(args.chain, args.token_address))
    except (DexscreenerError, ValueError) as exc:
        print(f"viral-mint: {exc}", file=sys.stderr)
        code = 1
    raise SystemExit(code)


if __name__ == "__main__":
    main()
