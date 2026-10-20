from datetime import datetime, timezone
import pytest
from viral_mint.history import Snapshot, SnapshotStore
from viral_mint.ranking import rank_observed_pools

def sample(ts, pair="pool", liquidity=25000, score=20, volume=100):
    return Snapshot(ts, "solana", f"token-{pair}", pair, pair.upper(), 1.0, liquidity, volume,
                    10, 8, score, ())

def test_rank_applies_liquidity_and_observation_gates():
    now = datetime(2026, 10, 20, 12, tzinfo=timezone.utc)
    data = [sample(f"2026-10-20T{hour:02d}:00:00+00:00", score=score, volume=volume)
            for hour, score, volume in [(9, 20, 100), (10, 30, 120), (11, 50, 180)]]
    data += [sample("2026-10-20T11:00:00+00:00", pair="thin", liquidity=100, score=99)]
    data += [sample("2026-10-20T11:00:00+00:00", pair="new", score=100)]
    result = rank_observed_pools(data, now=now, min_liquidity_usd=10000)
    assert result["ranked_count"] == 1
    assert result["ranked"][0]["pair_address"] == "pool"
    assert result["ranked"][0]["rank"] == 1
    assert result["excluded_count"] == 2

def test_rank_validates_filters():
    with pytest.raises(ValueError):
        rank_observed_pools([], min_liquidity_usd=-1)
    with pytest.raises(ValueError):
        rank_observed_pools([], min_observations=1)

def test_recent_snapshots_is_bounded():
    with SnapshotStore(":memory:") as store:
        store.add(sample("2026-10-20T10:00:00+00:00"))
        assert len(store.recent_snapshots()) == 1
        with pytest.raises(ValueError):
            store.recent_snapshots(0)
