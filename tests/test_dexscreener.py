import httpx
import pytest
import respx

from viral_mint.dexscreener import DexscreenerClient, DexscreenerError


@pytest.mark.asyncio
@respx.mock
async def test_fetches_and_normalizes_token_pairs():
    respx.get("https://api.dexscreener.com/token-pairs/v1/solana/token123").mock(
        return_value=httpx.Response(200, json=[{
            "chainId": "solana", "pairAddress": "pair123", "dexId": "raydium",
            "baseToken": {"address": "token123", "name": "Example", "symbol": "EX"},
            "quoteToken": {"address": "quote", "symbol": "USDC"},
            "liquidity": {"usd": 15000}, "volume": {"h1": 4000},
            "txns": {"h1": {"buys": 20, "sells": 12}},
            "priceChange": {"h1": 2.1},
        }])
    )
    async with DexscreenerClient() as client:
        pairs = await client.get_token_pairs("solana", "token123")
    assert len(pairs) == 1
    assert pairs[0].pair_address == "pair123"
    assert pairs[0].liquidity_usd == 15000.0


@pytest.mark.asyncio
@respx.mock
async def test_rejects_non_array_payload():
    respx.get("https://api.dexscreener.com/token-pairs/v1/solana/token123").mock(
        return_value=httpx.Response(200, json={"error": "unexpected"})
    )
    async with DexscreenerClient() as client:
        with pytest.raises(DexscreenerError, match="expected a JSON array"):
            await client.get_token_pairs("solana", "token123")


@pytest.mark.asyncio
async def test_requires_chain_and_address():
    async with DexscreenerClient() as client:
        with pytest.raises(ValueError):
            await client.get_token_pairs("", "token123")
