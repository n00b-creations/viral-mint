"""CSV exports for locally stored ViralMint observations."""
from __future__ import annotations
import csv
from pathlib import Path
from dataclasses import asdict
from viral_mint.history import SnapshotStore

FIELDS = [
    "observed_at", "chain_id", "token_address", "pair_address", "symbol",
    "price_usd", "liquidity_usd", "volume_h1_usd", "buys_h1", "sells_h1",
    "market_activity_score", "warnings",
]

def export_snapshots_csv(db_path: str, output_path: str, limit: int = 100000) -> dict:
    """Export newest stored observations as CSV; output directory is created if needed."""
    if limit < 1 or limit > 100000:
        raise ValueError("limit must be between 1 and 100000")
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with SnapshotStore(db_path) as store:
        rows = store.recent_snapshots(limit=limit)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for snapshot in rows:
            record = asdict(snapshot)
            record["warnings"] = " | ".join(snapshot.warnings)
            writer.writerow({key: record.get(key) for key in FIELDS})
    missing_liquidity = sum(row.liquidity_usd is None for row in rows)
    missing_price = sum(row.price_usd is None for row in rows)
    missing_volume = sum(row.volume_h1_usd is None for row in rows)
    warning_rows = sum(bool(row.warnings) for row in rows)
    return {
        "status": "ok", "output": str(output), "rows_exported": len(rows),
        "database": db_path,
        "data_quality": {
            "rows_with_warnings": warning_rows,
            "missing_price_rows": missing_price,
            "missing_liquidity_rows": missing_liquidity,
            "missing_one_hour_volume_rows": missing_volume,
        },
    }
