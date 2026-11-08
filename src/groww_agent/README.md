# Application source

The current code contains domain models, a validated paper-only CLI foundation,
and a SQLite record store. The instrument-universe model covers the requested
NSE/BSE cash equities and Groww-supported ETFs with exchange-qualified listings
and swing-only style. The verified listing catalog is not loaded, so the default
universe is empty; it must fail closed rather than invent candidates.

The implemented local foundation validates paper-only configuration and persists
sessions, signals, approvals, order intents, paper orders, fills, positions,
append-only audit events, and fail-closed startup recovery state. Daily OHLCV CSV
data can be validated and scanned into a technical-only watchlist. A portfolio
snapshot can account for fills when the caller provides current marks; a missing
position mark makes net liquidation unavailable. Trade entry processing is disabled.
The intended modular monolith has
boundaries for market-data adapters, validation, scanner/strategy, optional AI
explanation, approval, independent risk, paper order simulation, portfolio
ledger/recovery, Telegram, persistence, and monitoring. There is no live order
adapter or funded-account integration.

See `docs/high-level-design.md` and `docs/WORK-TRACKER.md`. `groww-agent start`
initializes state, records that recovery is required, and exits; it is not a
continuous trading process. T13 remains blocked by unverified providers,
simulation assumptions, and numerical strategy exits. Do not treat domain-model
placeholders as accepted operational values or runtime enforcement.
