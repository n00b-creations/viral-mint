"""SQLite-backed timestamped market observations and trend calculations."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from viral_mint.models import MarketPair
from viral_mint.scoring import score_pair


@dataclass(frozen=True, slots=True)
class Snapshot:
    observed_at: str
    chain_id: str
    token_address: str
    pair_address: str
    symbol: str
    price_usd: float | None
    liquidity_usd: float | None
    volume_h1_usd: float | None
    buys_h1: int | None
    sells_h1: int | None
    market_activity_score: int
    warnings: tuple[str, ...]

    @classmethod
    def from_pair(cls, pair: MarketPair, observed_at: str | None = None) -> "Snapshot":
        score = score_pair(pair)
        return cls(
            observed_at=observed_at or datetime.now(timezone.utc).isoformat(),
            chain_id=pair.chain_id,
            token_address=pair.base_token.address,
            pair_address=pair.pair_address,
            symbol=pair.base_token.symbol,
            price_usd=pair.price_usd,
            liquidity_usd=pair.liquidity_usd,
            volume_h1_usd=pair.volume_h1_usd,
            buys_h1=pair.buys_h1,
            sells_h1=pair.sells_h1,
            market_activity_score=score.score,
            warnings=score.warnings,
        )


class SnapshotStore:
    """Persist observations locally in SQLite; no remote database is used."""

    def __init__(self, path: str | Path = "data/viral_mint.sqlite3"):
        self.path = Path(path)
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(self.path))
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                observed_at TEXT NOT NULL,
                chain_id TEXT NOT NULL,
                token_address TEXT NOT NULL,
                pair_address TEXT NOT NULL,
                symbol TEXT NOT NULL,
                price_usd REAL,
                liquidity_usd REAL,
                volume_h1_usd REAL,
                buys_h1 INTEGER,
                sells_h1 INTEGER,
                market_activity_score INTEGER NOT NULL,
                warnings_json TEXT NOT NULL
            )
        """)
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_snapshots_pair_time "
            "ON snapshots(chain_id, token_address, pair_address, observed_at, id)"
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "SnapshotStore":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def add(self, snapshot: Snapshot) -> int:
        cursor = self.connection.execute("""
            INSERT INTO snapshots (
                observed_at, chain_id, token_address, pair_address, symbol,
                price_usd, liquidity_usd, volume_h1_usd, buys_h1, sells_h1,
                market_activity_score, warnings_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            snapshot.observed_at, snapshot.chain_id, snapshot.token_address,
            snapshot.pair_address, snapshot.symbol, snapshot.price_usd,
            snapshot.liquidity_usd, snapshot.volume_h1_usd, snapshot.buys_h1,
            snapshot.sells_h1, snapshot.market_activity_score,
            json.dumps(list(snapshot.warnings)),
        ))
        self.connection.commit()
        return int(cursor.lastrowid)

    def history(self, chain_id: str, token_address: str, pair_address: str, limit: int = 20) -> list[Snapshot]:
        if limit < 1 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        rows = self.connection.execute("""
            SELECT * FROM snapshots
            WHERE chain_id = ? AND token_address = ? AND pair_address = ?
            ORDER BY observed_at DESC, id DESC LIMIT ?
        """, (chain_id, token_address, pair_address, limit)).fetchall()
        snapshots = [
            Snapshot(
                observed_at=row["observed_at"], chain_id=row["chain_id"],
                token_address=row["token_address"], pair_address=row["pair_address"],
                symbol=row["symbol"], price_usd=row["price_usd"],
                liquidity_usd=row["liquidity_usd"], volume_h1_usd=row["volume_h1_usd"],
                buys_h1=row["buys_h1"], sells_h1=row["sells_h1"],
                market_activity_score=row["market_activity_score"],
                warnings=tuple(json.loads(row["warnings_json"])),
            )
            for row in rows
        ]
        return list(reversed(snapshots))


def _change(previous: float | int | None, current: float | int | None) -> dict[str, float | None]:
    if previous is None or current is None:
        return {"absolute": None, "percent": None}
    absolute = float(current) - float(previous)
    percent = None if float(previous) == 0 else absolute / abs(float(previous)) * 100
    return {
        "absolute": round(absolute, 8),
        "percent": round(percent, 4) if percent is not None else None,
    }


def analyze_trend(snapshots: list[Snapshot]) -> dict:
    """Compare recent observations; acceleration is reported only with 3 samples.

    Rates are per hour, derived from actual timestamp gaps. This is descriptive
    telemetry, not a predictive signal; sparse or irregular samples are labeled.
    """
    ordered = sorted(snapshots, key=lambda item: item.observed_at)
    if len(ordered) < 2:
        return {
            "observations": len(ordered),
            "status": "insufficient_history",
            "message": "Collect at least two snapshots of the same pool to compare changes.",
        }

    previous, current = ordered[-2], ordered[-1]
    metrics = ("price_usd", "liquidity_usd", "volume_h1_usd", "market_activity_score")
    changes = {metric: _change(getattr(previous, metric), getattr(current, metric)) for metric in metrics}
    try:
        t0 = datetime.fromisoformat(previous.observed_at.replace("Z", "+00:00"))
        t1 = datetime.fromisoformat(current.observed_at.replace("Z", "+00:00"))
        hours = (t1 - t0).total_seconds() / 3600
    except ValueError:
        hours = 0
    if hours <= 0:
        rate_warning = "Observation timestamps are not increasing; hourly rates unavailable."
        hours = 0
    else:
        rate_warning = None

    acceleration = {}
    if len(ordered) >= 3:
        older, earlier = ordered[-3], ordered[-2]
        try:
            t_old = datetime.fromisoformat(older.observed_at.replace("Z", "+00:00"))
            t_mid = datetime.fromisoformat(earlier.observed_at.replace("Z", "+00:00"))
            old_hours = (t_mid - t_old).total_seconds() / 3600
        except ValueError:
            old_hours = 0
        if old_hours > 0 and hours > 0:
            for metric in ("volume_h1_usd", "market_activity_score"):
                first = _change(getattr(older, metric), getattr(earlier, metric))["absolute"]
                second = changes[metric]["absolute"]
                acceleration[metric] = {
                    "previous_change_per_hour": round(first / old_hours, 6) if first is not None else None,
                    "latest_change_per_hour": round(second / hours, 6) if second is not None else None,
                    "rate_change_per_hour": round(second / hours - first / old_hours, 6) if first is not None and second is not None else None,
                }
        else:
            acceleration["warning"] = "Cannot estimate acceleration from non-increasing or invalid timestamps."

    result = {
        "observations": len(ordered),
        "status": "ok",
        "pair_address": current.pair_address,
        "symbol": current.symbol,
        "from": previous.observed_at,
        "to": current.observed_at,
        "elapsed_hours": round(hours, 6) if hours > 0 else None,
        "changes": changes,
        "hourly_rates": {
            metric: round(change["absolute"] / hours, 8) if hours > 0 and change["absolute"] is not None else None
            for metric, change in changes.items()
        },
        "acceleration": acceleration if len(ordered) >= 3 else None,
        "warnings": list(current.warnings),
    }
    if rate_warning:
        result["warnings"].append(rate_warning)
    if len(ordered) < 3:
        result["warnings"].append("Acceleration unavailable: collect at least three observations.")
    result["warnings"].append("Historical deltas describe observed snapshots; they do not predict future performance.")
    return result
