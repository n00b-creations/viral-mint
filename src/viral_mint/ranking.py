"""Rank already-observed pools; this is not market-wide discovery or prediction."""
from datetime import datetime, timezone
from viral_mint.history import Snapshot, analyze_trend

def rank_observed_pools(snapshots: list[Snapshot], min_liquidity_usd: float = 10000.0,
                        max_age_hours: float = 6.0, min_observations: int = 3,
                        limit: int = 25, now: datetime | None = None) -> dict:
    if min_liquidity_usd < 0 or max_age_hours <= 0 or min_observations < 2 or not 1 <= limit <= 1000:
        raise ValueError("Invalid ranking filters: liquidity >= 0, age > 0, observations >= 2, limit 1-1000.")
    now = now or datetime.now(timezone.utc)
    groups = {}
    for item in snapshots:
        groups.setdefault((item.chain_id, item.token_address, item.pair_address), []).append(item)
    ranked, excluded = [], []
    for (chain, token, pair), rows in groups.items():
        rows.sort(key=lambda x: x.observed_at)
        latest = rows[-1]
        reasons = []
        try:
            age = (now - datetime.fromisoformat(latest.observed_at.replace("Z", "+00:00"))).total_seconds() / 3600
        except ValueError:
            age = float("inf")
        if age < 0 or age > max_age_hours: reasons.append("stale_or_invalid_timestamp")
        if latest.liquidity_usd is None or latest.liquidity_usd < min_liquidity_usd: reasons.append("below_liquidity_floor_or_missing")
        if len(rows) < min_observations: reasons.append("insufficient_observations")
        if reasons:
            excluded.append({"chain_id": chain, "token_address": token, "pair_address": pair, "reasons": reasons})
            continue
        trend = analyze_trend(rows)
        score_delta = trend.get("changes", {}).get("market_activity_score", {}).get("absolute")
        volume_delta = trend.get("changes", {}).get("volume_h1_usd", {}).get("absolute")
        ranked.append({
            "chain_id": chain, "token_address": token, "pair_address": pair, "symbol": latest.symbol,
            "observations": len(rows), "age_hours": round(age, 3), "liquidity_usd": latest.liquidity_usd,
            "market_activity_score": latest.market_activity_score, "score_change_since_previous": score_delta,
            "rolling_volume_h1_change_since_previous": volume_delta, "warnings": list(latest.warnings),
            "_key": (latest.market_activity_score, score_delta if score_delta is not None else float("-inf"),
                     volume_delta if volume_delta is not None else float("-inf")),
        })
    ranked.sort(key=lambda x: x["_key"], reverse=True)
    ranked = ranked[:limit]
    for i, item in enumerate(ranked, 1):
        item["rank"] = i
        del item["_key"]
    return {
        "status": "ok", "ranked_count": len(ranked), "excluded_count": len(excluded),
        "filters": {"min_liquidity_usd": min_liquidity_usd, "max_age_hours": max_age_hours,
                    "min_observations": min_observations, "limit": limit},
        "ranking_basis": ["latest market-activity score descending", "score change descending",
                          "rolling one-hour volume-field change descending"],
        "limitations": ["Only pools already stored in this local database are considered.",
                        "Rolling-window volume deltas are not exact traded volume between observations.",
                        "Activity scores and ranks do not predict virality, safety, or future returns."],
        "ranked": ranked, "excluded": excluded,
    }
