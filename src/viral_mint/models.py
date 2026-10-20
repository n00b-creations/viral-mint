"""Typed, defensive models for public market-pair data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


@dataclass(frozen=True, slots=True)
class Token:
    address: str
    name: str = ""
    symbol: str = ""

    @classmethod
    def from_payload(cls, payload: Any) -> "Token":
        if not isinstance(payload, dict):
            payload = {}
        return cls(
            address=str(payload.get("address") or ""),
            name=str(payload.get("name") or ""),
            symbol=str(payload.get("symbol") or ""),
        )


@dataclass(frozen=True, slots=True)
class MarketPair:
    chain_id: str
    pair_address: str
    dex_id: str
    url: str
    base_token: Token
    quote_token: Token
    price_usd: float | None
    liquidity_usd: float | None
    volume_h24_usd: float | None
    volume_h6_usd: float | None
    volume_h1_usd: float | None
    buys_h1: int | None
    sells_h1: int | None
    price_change_h1_pct: float | None
    pair_created_at_ms: int | None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "MarketPair":
        liquidity = payload.get("liquidity") if isinstance(payload.get("liquidity"), dict) else {}
        volume = payload.get("volume") if isinstance(payload.get("volume"), dict) else {}
        txns = payload.get("txns") if isinstance(payload.get("txns"), dict) else {}
        h1 = txns.get("h1") if isinstance(txns.get("h1"), dict) else {}
        change = payload.get("priceChange") if isinstance(payload.get("priceChange"), dict) else {}
        created = payload.get("pairCreatedAt")
        try:
            created_ms = int(created) if created is not None else None
        except (TypeError, ValueError, OverflowError):
            created_ms = None

        def integer(value: Any) -> int | None:
            n = _number(value)
            return int(n) if n is not None and n >= 0 else None

        return cls(
            chain_id=str(payload.get("chainId") or ""),
            pair_address=str(payload.get("pairAddress") or ""),
            dex_id=str(payload.get("dexId") or ""),
            url=str(payload.get("url") or ""),
            base_token=Token.from_payload(payload.get("baseToken")),
            quote_token=Token.from_payload(payload.get("quoteToken")),
            price_usd=_number(payload.get("priceUsd")),
            liquidity_usd=_number(liquidity.get("usd")),
            volume_h24_usd=_number(volume.get("h24")),
            volume_h6_usd=_number(volume.get("h6")),
            volume_h1_usd=_number(volume.get("h1")),
            buys_h1=integer(h1.get("buys")),
            sells_h1=integer(h1.get("sells")),
            price_change_h1_pct=_number(change.get("h1")),
            pair_created_at_ms=created_ms,
        )
