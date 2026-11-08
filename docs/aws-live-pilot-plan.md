# AWS-hosted Groww pilot — cost and go-live plan

**Status:** planning only. No AWS resources have been created, no Groww
credentials have been collected, and no live orders have been enabled.

## Agreed direction

- Target a single AWS-hosted application in Mumbai (`ap-south-1`).
- Use Groww's official Trading API only after the account owner activates and
  verifies the required API subscription.
- Keep proposed live capital at or below INR 3,000. Live trading remains disabled
  until the application is staged, verified, and the owner gives a separate
  go-live confirmation.
- Start the application before the Indian cash-market pre-open, reconcile account
  and order state, and stop the EC2 compute after the close and a clean shutdown.
- The owner accepts stopping at 16:00 IST while carrying swing positions and
  accepting overnight gap risk; reconcile before the next market session.
- The owner accepted the pilot limits below for staging design only. This is not
  approval to enable live orders.
- Set an AWS Budget notification threshold of INR 1,000/month when deployment is
  later authorized. This is an alert, not a hard spend cap.
- First phase is a deterministic rules-based pilot, not model training. Backtests
  and paper evaluation are needed before any live order; the system must not
  “learn” by changing rules while trading.
- The current authorization is to prepare this plan only. Provisioning, paid
  subscriptions, secret entry, and live orders are not authorized by this plan.

## Proposed daily operation

1. EventBridge Scheduler starts the EBS-backed EC2 instance at **08:15 IST** on
   exchange weekdays. The application validates configuration, obtains approved
   market/session data, reconciles Groww positions/orders, and remains in
   `RECOVERY_REQUIRED` if any check fails.
2. Before sending any candidate proposal, collect a timestamped evidence bundle
   covering global market closes/current indications, material global macro and
   geopolitical events, India-market/index context, scheduled India/global events,
   and current company/stock/ETF-specific news. Keep source URLs, publication
   times, retrieval times, and data-health/freshness checks with the decision.
3. AI must assess that evidence and return a cited `FAVORABLE`, `UNFAVORABLE`, or
   `UNCERTAIN` market decision with a concise explanation and key risks. It must
   not invent missing news or treat technical signals alone as a market
   assessment. Missing, stale, conflicting, or high-impact unresolved evidence,
   or any decision other than `FAVORABLE`, means **no trade** and an alert/report.
   The risk engine, approved exposure limits, and owner approval remain
   deterministic gates that AI cannot override.
4. Before pre-open analysis, check the exchange holiday calendar. A weekday
   market holiday must produce a safe no-trade exit. Revalidate market conditions
   after open using current data before any approved entry is eligible.
5. During the session, deterministic entry/exit rules run only when all gates pass.
   Order and fill events are durably recorded and reconciled; uncertain outcomes
   stop new entries.
6. After the cash-market close, stop new entries, reconcile pending/open orders,
   persist a shutdown checkpoint, deliver the daily report, and request a graceful
   EC2 stop at **16:00 IST**. A later stop schedule may be used as a failsafe, not
   as a substitute for clean application shutdown.
7. On the next market day, restart and reconcile before any activity.

This evidence-driven AI market/news assessment is a required product feature, not
implemented in the current CSV validator/watchlist. The watchlist is technical
only and cannot authorize entries. Provider/source selection, coverage,
licensing, freshness thresholds, and recurring AI/news costs must be verified
before this assessment can run in AWS.

EventBridge Scheduler supports named IANA time zones such as `Asia/Kolkata` and
cron schedules, with up to 60 seconds of invocation precision. Weekday cron rules
alone do not know exchange holidays; the application must use a verified calendar.

**Accepted overnight behavior and risk:** The owner chose to stop EC2 at 16:00 IST
and accept overnight gap risk while positions may remain open. Groww's published API annexure documents order validity as
`DAY`. Do not assume a protective stop survives market close or remains active
overnight. With swing holdings, the next session's stop/target check can only act
when the application and market feed are available; an overnight gap can exceed
the stop and the eventual exit price can be worse. A broker-side persistent/GTT
exit must not be assumed unless Groww confirms it is available for this API and
the exact cash-equity order type. If that cannot be verified, the owner must
choose between accepting gap risk, keeping the process available for monitoring,
or changing the holding policy.

## Preliminary AWS monthly estimate

Planning assumptions: one small Linux ARM instance (candidate `t4g.small`),
approximately 8 hours/day, 22 weekdays/month (about 176 instance-hours), 8–16 GB
gp3 EBS, one public IPv4 while running, low-volume logs, no NAT Gateway, no load
balancer, no database server, and no GPU/model-training workload.

| Cost component | Preliminary monthly range |
|---|---:|
| EC2 compute for scheduled hours | INR 300–450 |
| EBS root/data volume retained while stopped | INR 60–150 |
| Public IPv4 while running and small network usage | INR 70–150 |
| Scheduler, low-volume logs/alarms, secret storage and backup allowance | INR 100–250 |
| **AWS planning envelope** | **about INR 600–1,000/month, before applicable taxes or account-specific credits** |

This is a budgeting estimate, not a quote or a hard AWS spend limit. The owner's
INR 1,000/month AWS Budget threshold is a notification setting, not a cap that
prevents charges above that amount. Actual
Mumbai-region rates, instance availability, currency conversion, taxes, backups,
logs, and usage must be entered into the AWS Pricing Calculator before approval.
Stopped EC2 compute is not billed, but EBS and other retained resources can
continue billing. Avoid a NAT Gateway for this small single-host design; it has
an hourly charge even at low traffic. Configure AWS Budgets alerts, but understand
that a budget alert is not a hard spending cap.

The estimate excludes Groww API subscription, brokerage, statutory taxes/fees,
and any market/news/AI subscription. Groww's official Python API guide says an
active Trading API subscription is required; the current subscription price and
plan entitlements must be checked in the owner's Groww account. Do not proceed if
the combined recurring cost is unacceptable relative to INR 3,000 capital.

## Conservative live-pilot limits — accepted for staging design only

The owner accepted these numbers for staging design only; they do not activate
trading or authorize a live-order path.

| Control | Proposed initial setting |
|---|---:|
| Total paper/live capital exposed | INR 3,000 hard cap; no external balance top-up |
| Product scope | Delivery cash equities only; long-only; CNC; no F&O, MIS, MTF, leverage, or short selling |
| Planned risk per position | INR 15 maximum before costs (0.5% of INR 3,000) |
| Daily entry lock | INR 45 loss (1.5%); sticky for the session, blocks entries but does not force-close holdings |
| Gross exposure | INR 2,400 maximum (80% of capital) |
| Single instrument/issuer exposure | INR 600 maximum (20% of capital) |
| Initial concurrent positions | One |
| New entries | At most one per session; a new entry after exit needs a fresh authenticated approval |
| Exit rule | Owner-selected 2% net-profit target after costs and 2% protective stop below actual fill; no fixed age exit |
| Manual authorization | Exact proposal approval required before each entry batch; independent hard-risk checks still apply |

At a 2% stop, INR 600 exposure implies about INR 12 price risk before charges and
gaps. This is within the INR 15 proposed planned-risk limit, but does not cap
actual losses. A gap, outage, rejected order, or illiquid instrument can cause a
larger loss. The daily INR 45 threshold is an entry lock, not a guaranteed maximum
loss.

Costs matter disproportionately at this account size. Groww's public equity
pricing page lists brokerage as INR 20 or 0.1% per executed order, whichever is
lower, with a INR 5 minimum, plus statutory charges and delivery sell-side DP
charges where applicable. On a small position, a round trip can consume a
material fraction of a 2% target. Calculate each instrument/order's exact
estimated charges before proposing it; if the net target is not viable after
costs, do not trade.

## Required gates before any deployment

1. Owner has accepted the numeric limits for staging design and accepts overnight
   gap risk. A separate live go-live confirmation remains required.
2. Owner verifies Groww API account eligibility, subscription price/terms, cash
   order support, rate limits, and order persistence behavior in the official
   dashboard/docs.
3. Implement and test a separate read-only/reconciliation stage, then a simulator
   and paper evaluation. No live order path in staging.
4. Implement secret storage and rotation without sending credentials through chat
   or committing them to the repository.
5. Produce an itemized AWS Calculator estimate before provisioning. Configure the
   accepted INR 1,000/month budget alert and least-privilege IAM; the alert is not
   a hard cap, so provisioning still requires a separate spend approval.
6. Test start/stop schedules, market holidays, crash recovery, duplicate/unknown
   orders, stale data, API outage, gaps, and backup restoration.
7. Obtain an explicit separate go-live confirmation before enabling even a
   INR 1 real order. Keep an owner-operated kill switch and Groww app fallback.

## Official references checked

- [Groww Trading API Python SDK guide](https://groww.in/trade-api/docs/python-sdk) — API functions, active subscription requirement, authentication, rate limits.
- [Groww order API](https://groww.in/trade-api/docs/python-sdk/orders) and [order annexures](https://groww.in/trade-api/docs/python-sdk/annexures) — order types/status and `DAY` validity.
- [Groww brokerage and charges](https://groww.in/pricing) — public equity pricing; confirm applicability/current values in the account.
- [AWS EC2 On-Demand pricing](https://aws.amazon.com/ec2/pricing/on-demand/) and [AWS Pricing Calculator](https://calculator.aws/) — region-specific quote required.
- [AWS EC2 stop/start behavior](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Stop_Start.html) — compute stop behavior and address changes.
- [AWS public IPv4 pricing behavior](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-ip-addressing.html#public-ipv4-addresses).
- [EventBridge Scheduler time zones and schedules](https://docs.aws.amazon.com/scheduler/latest/UserGuide/schedule-types.html).
