# Verification

Run the implemented T01 unit tests from the repository root with:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The instrument-universe tests cover the initial NSE equity symbols, cash-equity classification, allowed intraday/swing styles, and excluded asset classes. Future tests should cover sizing and exposure boundaries, persistent loss locks, approval expiry/replay, stale data, duplicate intents, unknown outcomes, restart reconciliation, backup restoration, and absence of real-order submission paths.

Trading runtime tests are not implemented yet.
