# Changelog

## Unreleased

- Initialized the standalone ViralMint repository.
- Added a typed pair model and public Dexscreener client.
- Added an explainable 0–100 market-activity heuristic with explicit missing-data warnings.
- Added a token query CLI that emits JSON.
- Added a local SQLite snapshot store and history command for descriptive deltas, hourly rates, and three-observation rate-change estimates.
- Added offline tests for market parsing, scoring, API responses, and historical calculations.
- Added a GitHub Actions test workflow.

- Added a local ranking command for previously observed pools with liquidity, freshness, and observation-count gates.
- Ranking reports exclusions and clearly states that it is not market-wide discovery or a predictive signal.
- Added tests for ranking behavior and bounded recent snapshot retrieval.

- Added bounded retries for transient HTTP and transport failures, including capped Retry-After handling.
- Added continuous local watchlist collection with per-token failure reporting and cycle summaries.
- Added CSV export for stored observations with missing-field and warning counts.
- Added offline tests for retries and CSV export.
