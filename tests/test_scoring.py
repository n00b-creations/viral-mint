from viral_mint.models import MarketPair, Token
from viral_mint.scoring import score_pair


def pair(**overrides):
    values = dict(
        chain_id="solana", pair_address="pair", dex_id="test", url="",
        base_token=Token(address="token", name="Example", symbol="EX"),
        quote_token=Token(address="quote", symbol="USD"),
        price_usd=1.0, liquidity_usd=10_000.0, volume_h24_usd=100_000.0,
        volume_h6_usd=20_000.0, volume_h1_usd=5_000.0, buys_h1=40,
        sells_h1=25, price_change_h1_pct=4.5, pair_created_at_ms=None,
    )
    values.update(overrides)
    return MarketPair(**values)


def test_score_is_bounded_and_explained():
    result = score_pair(pair())
    assert 0 <= result.score <= 100
    assert set(result.components) == {
        "liquidity", "volume_h1", "transactions_h1", "price_movement_h1"
    }
    assert any("not a social-virality" in warning for warning in result.warnings)


def test_missing_data_reduces_coverage_and_is_disclosed():
    result = score_pair(pair(liquidity_usd=None, volume_h1_usd=None))
    assert 0 <= result.score <= 100
    assert "liquidity" not in result.components
    assert "volume_h1" not in result.components
    assert any("Partial data coverage" in warning for warning in result.warnings)


def test_no_usable_data_returns_zero_with_warning():
    result = score_pair(pair(
        liquidity_usd=None, volume_h1_usd=None,
        buys_h1=None, sells_h1=None, price_change_h1_pct=None,
    ))
    assert result.score == 0
    assert not result.components
    assert any("not informative" in warning for warning in result.warnings)


def test_price_movement_is_magnitude_not_direction():
    positive = score_pair(pair(price_change_h1_pct=20)).components["price_movement_h1"]
    negative = score_pair(pair(price_change_h1_pct=-20)).components["price_movement_h1"]
    assert positive == negative
