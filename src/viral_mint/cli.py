"""Command-line entry point for token research, collection, and local history."""
from __future__ import annotations
import argparse
import asyncio
import json
import sys
from dataclasses import asdict
from pathlib import Path
from viral_mint.csv_export import export_snapshots_csv
from viral_mint.dexscreener import DexscreenerClient, DexscreenerError
from viral_mint.history import Snapshot, SnapshotStore, analyze_trend
from viral_mint.ranking import rank_observed_pools
from viral_mint.scoring import score_pair

async def _fetch_pairs(chain: str, address: str):
    async with DexscreenerClient() as client:
        return await client.get_token_pairs(chain, address)

def _pair_report(pair) -> dict:
    score = score_pair(pair)
    return {"chain_id": pair.chain_id, "pair_address": pair.pair_address, "dex_id": pair.dex_id,
            "url": pair.url, "token": {"name": pair.base_token.name, "symbol": pair.base_token.symbol,
            "address": pair.base_token.address}, "price_usd": pair.price_usd,
            "liquidity_usd": pair.liquidity_usd, "volume_h1_usd": pair.volume_h1_usd,
            "volume_h24_usd": pair.volume_h24_usd, "buys_h1": pair.buys_h1, "sells_h1": pair.sells_h1,
            "price_change_h1_pct": pair.price_change_h1_pct, "market_activity_score": score.score,
            "score_components": score.components, "warnings": list(score.warnings)}

async def _token_report(chain: str, address: str) -> int:
    pairs = await _fetch_pairs(chain, address)
    print(json.dumps({"chain": chain, "token_address": address, "pair_count": len(pairs),
                      "pairs": [_pair_report(pair) for pair in pairs]}, indent=2))
    return 0

async def _save_snapshot(chain: str, address: str, db_path: str) -> int:
    pairs = await _fetch_pairs(chain, address)
    with SnapshotStore(db_path) as store:
        saved = []
        for pair in pairs:
            snapshot = Snapshot.from_pair(pair, token_address=address)
            snapshot_id = store.add(snapshot)
            saved.append({"snapshot_id": snapshot_id, "observed_at": snapshot.observed_at,
                          "pair_address": pair.pair_address, "symbol": pair.base_token.symbol,
                          "market_activity_score": snapshot.market_activity_score,
                          "warnings": list(snapshot.warnings)})
    print(json.dumps({"chain": chain, "token_address": address, "database": db_path,
                      "saved_count": len(saved), "snapshots": saved,
                      "data_quality": {"pairs_returned": len(pairs),
                                       "pairs_with_warnings": sum(bool(x["warnings"]) for x in saved)},
                      "note": "A single observation is a baseline; trends require repeated snapshots."}, indent=2))
    return 0

def _show_history(chain: str, address: str, pair_address: str, db_path: str, limit: int) -> int:
    with SnapshotStore(db_path) as store:
        snapshots = store.history(chain, address, pair_address, limit=limit)
    result = analyze_trend(snapshots)
    result.update({"chain": chain, "token_address": address, "database": db_path,
                   "history": [asdict(item) for item in snapshots]})
    print(json.dumps(result, indent=2))
    return 0

async def _collect(watchlist_path: str, db_path: str, interval: int, cycles: int) -> int:
    try:
        payload = json.loads(Path(watchlist_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read watchlist JSON: {exc}") from exc
    if not isinstance(payload, list) or not payload:
        raise ValueError("Watchlist must be a non-empty JSON array of {chain, token_address} objects.")
    entries = []
    seen = set()
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("Every watchlist entry must be an object.")
        chain = str(item.get("chain", "")).strip()
        address = str(item.get("token_address", "")).strip()
        if not chain or not address:
            raise ValueError("Every watchlist entry needs non-empty chain and token_address fields.")
        if (chain, address) not in seen:
            entries.append((chain, address))
            seen.add((chain, address))
    cycle = 0
    while cycles == 0 or cycle < cycles:
        cycle += 1
        succeeded = failed = saved_count = 0
        with SnapshotStore(db_path) as store:
            for chain, address in entries:
                try:
                    pairs = await _fetch_pairs(chain, address)
                    for pair in pairs:
                        store.add(Snapshot.from_pair(pair, token_address=address))
                    saved_count += len(pairs)
                    succeeded += 1
                    warnings = sum(bool(score_pair(pair).warnings) for pair in pairs)
                    print(json.dumps({"event": "token_collected", "cycle": cycle, "chain": chain,
                                      "token_address": address, "pairs": len(pairs),
                                      "pairs_with_warnings": warnings}), flush=True)
                except (DexscreenerError, ValueError) as exc:
                    failed += 1
                    print(json.dumps({"event": "collection_failed", "cycle": cycle, "chain": chain,
                                      "token_address": address, "error": str(exc)}),
                          file=sys.stderr, flush=True)
        print(json.dumps({"event": "cycle_complete", "cycle": cycle, "tokens_succeeded": succeeded,
                          "tokens_failed": failed, "snapshots_saved": saved_count,
                          "watchlist_size": len(entries), "database": db_path}), flush=True)
        if cycles == 0 or cycle < cycles:
            await asyncio.sleep(interval)
    return 0

def main() -> None:
    parser = argparse.ArgumentParser(prog="viral-mint",
        description="Research public crypto market activity and track local historical observations.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    token = subparsers.add_parser("token", help="Fetch current market data for a token.")
    token.add_argument("token_address"); token.add_argument("--chain", required=True)
    snap = subparsers.add_parser("snapshot", help="Fetch current data and save timestamped snapshots locally.")
    snap.add_argument("token_address"); snap.add_argument("--chain", required=True)
    snap.add_argument("--db", default="data/viral_mint.sqlite3")
    hist = subparsers.add_parser("history", help="Compare historical observations for one pool.")
    hist.add_argument("token_address"); hist.add_argument("--chain", required=True); hist.add_argument("--pair", required=True)
    hist.add_argument("--db", default="data/viral_mint.sqlite3"); hist.add_argument("--limit", type=int, default=20)
    rank = subparsers.add_parser("rank", help="Rank pools already observed in the local database.")
    rank.add_argument("--db", default="data/viral_mint.sqlite3"); rank.add_argument("--min-liquidity", type=float, default=10000.0)
    rank.add_argument("--max-age-hours", type=float, default=6.0); rank.add_argument("--min-observations", type=int, default=3)
    rank.add_argument("--limit", type=int, default=25)
    collect = subparsers.add_parser("collect", help="Repeatedly collect snapshots from a JSON watchlist.")
    collect.add_argument("--watchlist", default="config/watchlist.json"); collect.add_argument("--db", default="data/viral_mint.sqlite3")
    collect.add_argument("--interval-seconds", type=int, default=900, help="Pause between collection cycles; minimum 30 seconds.")
    collect.add_argument("--cycles", type=int, default=0, help="Number of cycles; 0 runs until interrupted.")
    export = subparsers.add_parser("export-csv", help="Export stored observations to CSV with data-quality counts.")
    export.add_argument("--db", default="data/viral_mint.sqlite3"); export.add_argument("--output", default="exports/snapshots.csv")
    export.add_argument("--limit", type=int, default=100000)
    args = parser.parse_args()
    try:
        if args.command == "token":
            code = asyncio.run(_token_report(args.chain, args.token_address))
        elif args.command == "snapshot":
            code = asyncio.run(_save_snapshot(args.chain, args.token_address, args.db))
        elif args.command == "history":
            code = _show_history(args.chain, args.token_address, args.pair, args.db, args.limit)
        elif args.command == "rank":
            with SnapshotStore(args.db) as store: snapshots = store.recent_snapshots()
            result = rank_observed_pools(snapshots, min_liquidity_usd=args.min_liquidity,
                max_age_hours=args.max_age_hours, min_observations=args.min_observations, limit=args.limit)
            result["database"] = args.db
            print(json.dumps(result, indent=2)); code = 0
        elif args.command == "collect":
            if args.interval_seconds < 30: raise ValueError("interval-seconds must be at least 30 to avoid excessive API requests")
            if args.cycles < 0: raise ValueError("cycles must be zero (continuous) or positive")
            code = asyncio.run(_collect(args.watchlist, args.db, args.interval_seconds, args.cycles))
        else:
            print(json.dumps(export_snapshots_csv(args.db, args.output, args.limit), indent=2)); code = 0
    except (DexscreenerError, ValueError) as exc:
        print(f"viral-mint: {exc}", file=sys.stderr); code = 1
    raise SystemExit(code)

if __name__ == "__main__":
    main()
