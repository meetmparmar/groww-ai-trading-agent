# Architecture baseline

Logical flow: validated market data -> scanner/strategy -> optional AI explanation -> independent risk validation -> simulated order manager -> portfolio ledger/reconciliation -> Telegram reports and operations.

Session approval gates new entries. AI cannot approve sessions or override controls. Persistent intent/state records support recovery and duplicate prevention. A single EC2 instance is recoverable, not continuously available across host/AZ outages.

See the master work document for requirements, limits, failures, open decisions, and acceptance gates. This file explains the selected baseline; it does not resolve open implementation decisions.
