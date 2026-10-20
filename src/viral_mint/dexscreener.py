"""Async client for public Dexscreener token-pair endpoints, with bounded retries."""
from __future__ import annotations

import asyncio
import random
import httpx

from viral_mint.models import MarketPair


class DexscreenerError(RuntimeError):
    """Raised when the market-data service returns unusable data."""


class DexscreenerClient:
    BASE_URL = "https://api.dexscreener.com"
    RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}

    def __init__(self, timeout_seconds: float = 12.0, client: httpx.AsyncClient | None = None,
                 max_retries: int = 3, base_backoff_seconds: float = 0.5,
                 max_backoff_seconds: float = 8.0):
        if max_retries < 0 or max_retries > 8:
            raise ValueError("max_retries must be between 0 and 8")
        if base_backoff_seconds < 0 or max_backoff_seconds < base_backoff_seconds:
            raise ValueError("backoff values must be non-negative and max >= base")
        self.max_retries = max_retries
        self.base_backoff_seconds = base_backoff_seconds
        self.max_backoff_seconds = max_backoff_seconds
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=self.BASE_URL, timeout=httpx.Timeout(timeout_seconds),
            headers={"User-Agent": "ViralMint/0.1.0"},
        )

    async def __aenter__(self) -> "DexscreenerClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _get_with_retries(self, path: str) -> httpx.Response:
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.get(path)
                if response.status_code not in self.RETRYABLE_STATUS:
                    response.raise_for_status()
                    return response
                last_error = DexscreenerError(f"Transient HTTP status {response.status_code}")
                if attempt == self.max_retries:
                    response.raise_for_status()
                retry_after = response.headers.get("Retry-After")
            except httpx.HTTPError as exc:
                last_error = exc
                retry_after = None
                if attempt == self.max_retries:
                    raise DexscreenerError(f"Unable to retrieve token pairs after retries: {exc}") from exc
            if attempt < self.max_retries:
                exponential = min(self.max_backoff_seconds, self.base_backoff_seconds * (2 ** attempt))
                try:
                    delay = float(retry_after) if retry_after is not None else exponential
                except (ValueError, TypeError):
                    delay = exponential
                # Small jitter prevents synchronized clients; honor Retry-After without exceeding the cap.
                delay = min(self.max_backoff_seconds, max(0.0, delay))
                if delay:
                    await asyncio.sleep(delay + random.uniform(0, min(0.1, delay * 0.1)))
        raise DexscreenerError(f"Unable to retrieve token pairs: {last_error}")

    async def get_token_pairs(self, chain_id: str, token_address: str) -> list[MarketPair]:
        """Fetch pairs for a token address on the specified chain."""
        chain, address = chain_id.strip(), token_address.strip()
        if not chain or not address:
            raise ValueError("chain_id and token_address must be non-empty")
        try:
            response = await self._get_with_retries(f"/token-pairs/v1/{chain}/{address}")
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise DexscreenerError(f"Unable to retrieve token pairs: {exc}") from exc
        if not isinstance(payload, list):
            raise DexscreenerError("Unexpected response: expected a JSON array of pairs")
        return [MarketPair.from_payload(item) for item in payload if isinstance(item, dict)]
