"""Transparent heuristic scoring for observable market activity."""

from __future__ import annotations

import math
from dataclasses import dataclass

from viral_mint.models import MarketPair


@dataclass(frozen=True, slots=True)
class ScoreResult:
    score: int
    components: dict[str, float]
    warnings: tuple[str, ...]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def score_pair(pair: MarketPair) -> ScoreResult:
    """Return a 0–100 heuristic score; this is not a virality or safety prediction.

    Components use bounded logarithmic transforms so outliers cannot dominate
    without limit. Missing components are omitted and the remaining weights
    are renormalized; warnings disclose incomplete coverage.
    """
    warnings: list[str] = []
    components: dict[str, float] = {}
    weighted: list[tuple[float, float]] = []

    # Liquidity: $50k reaches the component ceiling. This is a configurable
    # heuristic threshold, not a universal definition of adequate liquidity.
    if pair.liquidity_usd is not None and pair.liquidity_usd >= 0:
        value = _clamp(math.log1p(pair.liquidity_usd) / math.log1p(50_000))
        components["liquidity"] = round(value * 100, 2)
        weighted.append((value, 0.30))
    else:
        warnings.append("Liquidity data missing; score coverage reduced.")

    # One-hour volume reaches the ceiling at $25k.
    if pair.volume_h1_usd is not None and pair.volume_h1_usd >= 0:
        value = _clamp(math.log1p(pair.volume_h1_usd) / math.log1p(25_000))
        components["volume_h1"] = round(value * 100, 2)
        weighted.append((value, 0.25))
    else:
        warnings.append("One-hour volume missing; score coverage reduced.")

    # Transaction count measures activity, not unique traders or organic demand.
    if pair.buys_h1 is not None and pair.sells_h1 is not None:
        tx_count = pair.buys_h1 + pair.sells_h1
        value = _clamp(math.log1p(tx_count) / math.log1p(200))
        components["transactions_h1"] = round(value * 100, 2)
        weighted.append((value, 0.25))
    else:
        warnings.append("One-hour transaction counts missing; score coverage reduced.")

    # Large absolute price changes are not automatically positive. This measures
    # movement magnitude and can be elevated during a crash as well as a rally.
    if pair.price_change_h1_pct is not None:
        value = _clamp(abs(pair.price_change_h1_pct) / 30.0)
        components["price_movement_h1"] = round(value * 100, 2)
        weighted.append((value, 0.20))
    else:
        warnings.append("One-hour price change missing; score coverage reduced.")

    if not weighted:
        warnings.append("No usable components; score defaults to 0 and is not informative.")
        return ScoreResult(score=0, components=components, warnings=tuple(warnings))

    total_weight = sum(weight for _, weight in weighted)
    score = round(100 * sum(value * weight for value, weight in weighted) / total_weight)
    if len(weighted) < 4:
        warnings.append(f"Partial data coverage: {len(weighted)} of 4 components available.")
    warnings.append("Market-activity heuristic only; not a social-virality, token-safety, or return prediction.")
    return ScoreResult(score=max(0, min(100, score)), components=components, warnings=tuple(warnings))
