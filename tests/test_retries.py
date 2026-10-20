import httpx
import pytest
import respx
from viral_mint.dexscreener import DexscreenerClient, DexscreenerError

@pytest.mark.asyncio
@respx.mock
async def test_retries_transient_server_error_then_succeeds():
    route = respx.get("https://api.dexscreener.com/token-pairs/v1/solana/token123")
    route.side_effect = [
        httpx.Response(503, json={"error": "temporary"}),
        httpx.Response(200, json=[]),
    ]
    async with DexscreenerClient(max_retries=1, base_backoff_seconds=0, max_backoff_seconds=0) as client:
        assert await client.get_token_pairs("solana", "token123") == []
    assert route.call_count == 2

@pytest.mark.asyncio
@respx.mock
async def test_does_not_retry_non_transient_client_error():
    route = respx.get("https://api.dexscreener.com/token-pairs/v1/solana/token123").mock(
        return_value=httpx.Response(400, json={"error": "bad request"})
    )
    async with DexscreenerClient(max_retries=3, base_backoff_seconds=0, max_backoff_seconds=0) as client:
        with pytest.raises(DexscreenerError, match="HTTP 400"):
            await client.get_token_pairs("solana", "token123")
    assert route.call_count == 1
