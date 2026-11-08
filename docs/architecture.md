# Architecture baseline

The paper-only system is designed as a modular monolith with explicit domain
boundaries, one authoritative portfolio-state writer, and durable decision/order
records. The logical flow is:

validated market data -> deterministic short-lived swing strategy -> optional
bounded AI explanation -> independent risk gate -> paper-only order simulator ->
portfolio ledger/reconciliation -> Telegram reports and controls.

Telegram approval gates each new entry batch. Automatic deterministic exits are
allowed only for already-approved positions; exits do not authorize reinvestment.
There is no live-order path or dependency on a funded Groww account. AI cannot
approve a session, alter controls, or submit orders.

The intended later deployment is one Linux EC2 host in Mumbai (`ap-south-1`) using
Docker Compose, after local validation and separate provisioning authorization.
A single host is recoverable, not continuously available through host/AZ outages.
No database, provider, instance size, or paid service is selected until its
capabilities, operational fit, and cost are verified.

See [high-level-design.md](./high-level-design.md) for component contracts, entry
and exit flows, logical state, trust boundaries, recovery behavior, and unresolved
gates. The design is not runtime implementation or authorization to provision.
