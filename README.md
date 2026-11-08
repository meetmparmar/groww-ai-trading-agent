# Groww AI Trading Agent

Local paper-trading application foundation for Indian equities. A complete
market-scanning or trading runtime and AWS deployment are not implemented.

## Layout

- `src/groww_agent/` — future Python application services.
- `tests/` — future unit, integration, recovery, and paper-isolation checks.
- `infra/terraform/` — future AWS infrastructure as code.
- `deploy/compose/` — future Docker Compose deployment configuration.
- `docs/` — architecture decisions and operations guidance.
- `docs/WORK-TRACKER.md` — authoritative requirements, decisions, and task tracker.

## Local development

Requires Python 3.10 or later. From the repository root in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The local foundation can be checked and initialized without connecting to a
broker or submitting orders:

```powershell
.\.venv\Scripts\python.exe -m groww_agent config-check
.\.venv\Scripts\python.exe -m groww_agent start
.\.venv\Scripts\python.exe -m groww_agent status
```

`start` initializes or migrates the local paper-state database and records a
startup recovery lock. It exits after initialization; it does not run a background
agent or submit simulated orders. `status` reports the persisted recovery lock.
Entries remain disabled until strategy, market data, approvals, portfolio risk,
and recovery are implemented and validated. Override the database location with
`GROWW_AGENT_DATABASE`; `APP_MODE` accepts only `paper`.

### Local CSV analysis

The current data adapter accepts completed daily OHLCV rows with these columns:
`date,symbol,exchange,open,high,low,close,volume`. Include a `NIFTY 50` benchmark
series and at least 51 daily bars per candidate to run the technical watchlist:

```powershell
.\.venv\Scripts\python.exe -m groww_agent validate-data --bars-file .\data\daily-bars.csv
.\.venv\Scripts\python.exe -m groww_agent scan --bars-file .\data\daily-bars.csv
```

`scan` is a technical watchlist only. It does not validate the data vendor,
freshness, listing eligibility, company/global news, or market events; it creates
no trade proposals, approvals, paper orders, or live orders. Its 2% stop reference
is relative to the latest CSV close, not an actual simulated fill. The chosen 2%
net-profit target cannot be calculated until the fill-cost model is implemented.

The included `data/daily-bars.csv` is **synthetic demo data**, including the
`SAMPLE` symbol and fabricated `NIFTY 50` values. It exists only to verify the
command and must never be treated as real market data or used to make investment
decisions. Replace it with appropriately licensed, verified data before analysis.

The virtual environment is local and ignored by Git. If Python was just installed while VS Code was open, restart VS Code so it picks up the updated user `PATH`. Alternatively, activate `.venv` with `.\.venv\Scripts\Activate.ps1` and use `python`.

## Baseline

The currently authorized release is paper trading only. The strategy direction is
short-lived swing: positions may cross sessions, are not force-sold at each close,
and should exit at the owner-selected 2% net-profit target after modeled costs or
2% protective stop below entry. There is no fixed maximum holding age; a brief
(often 2–3 session) horizon remains intent. Target execution still requires the
fill-cost and gap model. Requested instruments are listed Indian stocks and
Groww-supported ETFs on NSE and BSE. Paper capital defaults to ₹50,000, with a
₹100,000 ceiling, 0.5% planned risk per position, and a 1.5% daily loss entry lock.

The intended deployment baseline is one Linux EC2 instance in AWS Mumbai
(`ap-south-1`) with Docker Compose, but deployment and spending remain gated.
Kubernetes/EKS is out of scope.

## Current authorization

The owner wants to progress toward a Groww-connected live pilot capped at INR
3,000, with live orders allowed only after staging and a separate explicit
go-live confirmation. The current phase authorizes the costed plan and use of the accepted pilot limits
for staging design only. AWS provisioning, paid subscriptions, collecting/using
Groww credentials, and live orders are not authorized yet. The INR 1,000/month
AWS budget threshold is an alert, not a hard cap. Do not send credentials, OTPs,
or account details in chat.

## Next step

The [AWS pilot plan](docs/aws-live-pilot-plan.md) records the proposed schedule,
preliminary cost envelope, staging-design limits, and remaining go-live gates.
The intended pre-market AI assessment must use timestamped global markets,
global news/events, India-market context, and company/stock/ETF news, with a
cited no-trade outcome when evidence is unavailable or uncertain. This feature
is not implemented in the current CSV-only watchlist.
Groww API subscription, data permissions/freshness, simulation costs/gaps,
approval expiry, and recovery targets still need verification. The numerical
profit/stop/no-age rules are selected but not implemented as exits. No AWS
resources have been provisioned. See
[docs/WORK-TRACKER.md](docs/WORK-TRACKER.md) for authoritative statuses.

The local foundation CLI, CSV validator, technical watchlist, and SQLite record
store are implemented. The store can calculate a long-only paper portfolio
snapshot from recorded fills when valid marks are supplied; there is no automatic
data feed, approved strategy execution, approval transport, risk enforcement, or
order simulator. There is deliberately no Terraform apply command. This
repository is local; no remote repository has been created.
