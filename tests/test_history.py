from viral_mint.history import Snapshot, SnapshotStore, analyze_trend
from viral_mint.models import MarketPair, Token


def sample(ts, volume=100.0, score=20, pair_address="pool"):
    return Snapshot(
        observed_at=ts, chain_id="solana", token_address="mint", pair_address=pair_address,
        symbol="MINT", price_usd=1.0, liquidity_usd=1000.0,
        volume_h1_usd=volume, buys_h1=10, sells_h1=8,
        market_activity_score=score, warnings=(),
    )


def test_snapshot_store_round_trip_and_filter(tmp_path):
    db = tmp_path / "history.sqlite3"
    with SnapshotStore(db) as store:
        store.add(sample("2026-01-01T00:00:00+00:00"))
        store.add(sample("2026-01-01T01:00:00+00:00", volume=150))
        history = store.history("solana", "mint", "pool")
        assert len(history) == 2
        assert history[0].volume_h1_usd == 100
        assert history[1].volume_h1_usd == 150
        assert store.history("ethereum", "mint", "pool") == []


def test_trend_computes_deltas_and_acceleration():
    result = analyze_trend([
        sample("2026-01-01T00:00:00+00:00", volume=100, score=10),
        sample("2026-01-01T01:00:00+00:00", volume=150, score=20),
        sample("2026-01-01T02:00:00+00:00", volume=250, score=40),
    ])
    assert result["status"] == "ok"
    assert result["changes"]["volume_h1_usd"]["absolute"] == 100
    assert result["hourly_rates"]["volume_h1_usd"] == 100
    assert result["acceleration"]["volume_h1_usd"]["rate_change_per_hour"] == 50


def test_trend_requires_two_snapshots_and_three_for_acceleration():
    assert analyze_trend([sample("2026-01-01T00:00:00+00:00")])["status"] == "insufficient_history"
    result = analyze_trend([
        sample("2026-01-01T00:00:00+00:00"),
        sample("2026-01-01T01:00:00+00:00", volume=120),
    ])
    assert result["acceleration"] is None
    assert any("at least three" in warning for warning in result["warnings"])


def test_store_rejects_invalid_limit():
    with SnapshotStore(":memory:") as store:
        try:
            store.history("solana", "mint", "pool", limit=0)
        except ValueError as exc:
            assert "between 1 and 1000" in str(exc)
        else:
            raise AssertionError("expected ValueError")
