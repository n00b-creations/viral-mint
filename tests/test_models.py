from viral_mint.models import MarketPair


def test_pair_parser_handles_missing_and_malformed_values():
    pair = MarketPair.from_payload({
        "chainId": "solana",
        "baseToken": {"address": "abc", "symbol": "ABC"},
        "liquidity": {"usd": "not-a-number"},
        "volume": {"h1": 1234},
        "txns": {"h1": {"buys": "5", "sells": -1}},
        "priceChange": {"h1": "NaN"},
    })
    assert pair.chain_id == "solana"
    assert pair.base_token.symbol == "ABC"
    assert pair.liquidity_usd is None
    assert pair.volume_h1_usd == 1234.0
    assert pair.buys_h1 == 5
    assert pair.sells_h1 is None
    assert pair.price_change_h1_pct is None
