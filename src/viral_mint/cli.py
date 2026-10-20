"""Command-line entry point for token research and local history."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict

from viral_mint.dexscreener import DexscreenerClient, DexscreenerError
from viral_mint.history import Snapshot, SnapshotStore, analyze_trend
from viral_mint.scoring import score_pair


async def _fetch_pairs(chain: str, address: str):
    async with DexscreenerClient() as client:
        return await client.get_token_pairs(chain, address)


def _pair_report(pair) -> dict:
    score = score_pair(pair)
    return {
        "chain_id": pair.chain_id,
        "pair_address": pair.pair_address,
        "dex_id": pair.dex_id,
        "url": pair.url,
        "token": {
            "name": pair.base_token.name,
            "symbol": pair.base_token.symbol,
            "address": pair.base_token.address,
        },
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
    }


async def _token_report(chain: str, address: str) -> int:
    pairs = await _fetch_pairs(chain, address)
    print(json.dumps({
        "chain": chain, "token_address": address,
        "pair_count": len(pairs), "pairs": [_pair_report(pair) for pair in pairs],
    }, indent=2))
    return 0


async def _save_snapshot(chain: str, address: str, db_path: str) -> int:
    pairs = await _fetch_pairs(chain, address)
    with SnapshotStore(db_path) as store:
        saved = []
        for pair in pairs:
            snapshot = Snapshot.from_pair(pair, token_address=address)
            snapshot_id = store.add(snapshot)
            saved.append({
                "snapshot_id": snapshot_id,
                "observed_at": snapshot.observed_at,
                "pair_address": pair.pair_address,
                "symbol": pair.base_token.symbol,
                "market_activity_score": snapshot.market_activity_score,
                "warnings": list(snapshot.warnings),
            })
    print(json.dumps({
        "chain": chain, "token_address": address, "database": db_path,
        "saved_count": len(saved), "snapshots": saved,
        "note": "A single observation is a baseline; trend comparison requires repeated snapshots.",
    }, indent=2))
    return 0


def _show_history(chain: str, address: str, pair_address: str, db_path: str, limit: int) -> int:
    with SnapshotStore(db_path) as store:
        snapshots = store.history(chain, address, pair_address, limit=limit)
    result = analyze_trend(snapshots)
    result["chain"] = chain
    result["token_address"] = address
    result["database"] = db_path
    result["history"] = [asdict(item) for item in snapshots]
    print(json.dumps(result, indent=2))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="viral-mint",
        description="Research public crypto market activity and track local historical observations.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    token_parser = subparsers.add_parser("token", help="Fetch current market data for a token.")
    token_parser.add_argument("token_address")
    token_parser.add_argument("--chain", required=True, help="Dexscreener chain identifier, e.g. solana or ethereum.")

    snapshot_parser = subparsers.add_parser("snapshot", help="Fetch current data and save timestamped snapshots locally.")
    snapshot_parser.add_argument("token_address")
    snapshot_parser.add_argument("--chain", required=True)
    snapshot_parser.add_argument("--db", default="data/viral_mint.sqlite3", help="SQLite database path.")

    history_parser = subparsers.add_parser("history", help="Compare historical observations for one pool.")
    history_parser.add_argument("token_address")
    history_parser.add_argument("--chain", required=True)
    history_parser.add_argument("--pair", required=True, help="Exact pair address returned by the token or snapshot command.")
    history_parser.add_argument("--db", default="data/viral_mint.sqlite3")
    history_parser.add_argument("--limit", type=int, default=20, help="Number of recent observations to load (1–1000).")

    args = parser.parse_args()
    try:
        if args.command == "token":
            code = asyncio.run(_token_report(args.chain, args.token_address))
        elif args.command == "snapshot":
            code = asyncio.run(_save_snapshot(args.chain, args.token_address, args.db))
        else:
            code = _show_history(args.chain, args.token_address, args.pair, args.db, args.limit)
    except (DexscreenerError, ValueError) as exc:
        print(f"viral-mint: {exc}", file=sys.stderr)
        code = 1
    raise SystemExit(code)


if __name__ == "__main__":
    main()
