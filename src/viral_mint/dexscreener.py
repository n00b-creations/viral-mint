"""Async client for public Dexscreener token-pair endpoints."""

from __future__ import annotations

import httpx

from viral_mint.models import MarketPair


class DexscreenerError(RuntimeError):
    """Raised when the market-data service returns unusable data."""


class DexscreenerClient:
    BASE_URL = "https://api.dexscreener.com"

    def __init__(self, timeout_seconds: float = 12.0, client: httpx.AsyncClient | None = None):
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=httpx.Timeout(timeout_seconds),
            headers={"User-Agent": "ViralMint/0.1.0"},
        )

    async def __aenter__(self) -> "DexscreenerClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def get_token_pairs(self, chain_id: str, token_address: str) -> list[MarketPair]:
        """Fetch pairs for a token address on the specified chain."""
        chain = chain_id.strip()
        address = token_address.strip()
        if not chain or not address:
            raise ValueError("chain_id and token_address must be non-empty")
        try:
            response = await self._client.get(f"/token-pairs/v1/{chain}/{address}")
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise DexscreenerError(f"Unable to retrieve token pairs: {exc}") from exc

        if not isinstance(payload, list):
            raise DexscreenerError("Unexpected response: expected a JSON array of pairs")
        return [MarketPair.from_payload(item) for item in payload if isinstance(item, dict)]
