# Application source

The instrument-universe scope/model is implemented in `instruments.py`: all listed cash-equity stocks and Groww-supported ETFs on NSE and BSE, with exchange-qualified listings and no hard-coded symbol shortlist. The actual listing catalog is not loaded yet, so the default universe is empty and safely returns no candidates until a verified source is integrated. No trading runtime or live-order functionality exists.

Planned boundaries: market data, scanner, strategy, AI analysis, independent risk engine, simulated order management, portfolio/reconciliation, Telegram, persistence, monitoring.

Finalize interfaces and dependencies in T11–T13 before implementing these boundaries. Do not assume one process or container per logical service.
