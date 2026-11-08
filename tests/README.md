# Verification

Run the implemented T01 unit tests from the repository root with:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Instrument tests cover exchange-qualified equities/ETFs, swing-only styles and exclusions. Application tests cover paper-only configuration, CLI startup/status, persistent SQLite records across store instances, idempotency, basic order-state/fill boundaries, recovery migration/locks, ledger accounting, and audit redaction. Market-data and strategy tests cover OHLCV CSV validation and deterministic technical watchlist filters. Future tests should cover risk/exposure enforcement, Telegram identity/replay, stale market data, full restart reconciliation, backup restoration, and absence of real-order submission paths.

The CLI can validate local CSV data and produce a technical-only watchlist. It does not create trade proposals or orders; approval transport and an active trading runtime do not exist.
