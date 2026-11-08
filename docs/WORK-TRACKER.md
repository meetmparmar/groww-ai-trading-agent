# Groww AI Trading Agent — Requirements and Work Tracker

Version: 2.0 | Created: 7 November 2026 | Last updated: 8 November 2026

## Project dashboard

- Stage: Local foundation plus planning for an AWS-hosted Groww live pilot; no deployment or order path is authorized yet.
- Requirements and backlog: Owner wants a future live pilot capped at INR 3,000 after staging and separate go-live confirmation. Limits are accepted for staging design; AWS remains unprovisioned.
- Backlog: 51 tasks; 4 Done, 0 In progress, 10 Review, 1 Blocked, 36 Pending.
- Next action: Continue read-only/staging implementation and verify Groww subscription/API details. INR 1,000/month is an AWS budget alert, not a hard cap.
- Repository: Paper-only CLI, CSV validation/technical watchlist, SQLite records, restart recovery lock, and fill-based ledger snapshot; order execution remains disabled.
- AWS resources: Not provisioned.
- Real trading: Not enabled; future pilot requires staging and separate confirmation.

This is the master work document. Update it after each task or material decision. Documentation creation is complete but does not count as completion of any of the 51 delivery tasks.

## 1. Purpose and authorization

### Owner-stated desired product (scope review)

The owner wants an agent that uses current market information—including company/stock news and global events—to assess whether market conditions are suitable for trading, select promising stocks and ETFs for short-lived swing trades, explain and send proposed entries for approval, and manage positions with automatic exits. The latest requested end state is an AWS-hosted Groww pilot capped at INR 3,000, following staging and separate go-live confirmation.

The agent should independently rank candidates and seek risk-adjusted returns while controlling losses; the owner does not want to choose symbols from a list manually. No system can guarantee maximum profit or minimum loss. A market assessment may conclude that no trade is appropriate.

The owner previously authorized local paper-only implementation, then requested an AWS-hosted Groww pilot with no more than INR 3,000 capital. The owner accepted the pilot limits for staging design, a daily 08:15–16:00 IST schedule with overnight gap risk, and an INR 1,000/month AWS Budget alert. This does not authorize AWS provisioning, paid subscriptions, collecting/using Groww credentials, or live orders. Any future live orders require staged validation and a separate explicit go-live confirmation.

Source: the referenced “Refine Trading Agent Prompt” conversation and the planning specification and requirements backlog in this chat. Historical estimates are retained as planning inputs, not current quotations.

## 2. Confirmed requirements

| ID | Requirement |
|---|---|
| R01 | Current implementation has no live-order path. Desired future pilot: Groww-funded live delivery trading capped at INR 3,000, only after staging and separate go-live confirmation. |
| R02 | Groww is the intended integration; verify current API/data capabilities and restrictions. |
| R03 | All currently listed stocks and all NSE/BSE-listed ETFs supported by Groww are requested candidates for short-lived swing trading; the full listing catalog must be loaded from a verified source. Intraday is not part of the approved strategy. |
| R04 | Default simulated capital: ₹50,000, subject to session approval; maximum approved paper-capital ceiling: ₹100,000. |
| R05 | Maximum planned risk per trade: 0.5% of approved risk capital. |
| R06 | Daily loss circuit breaker: 1.5% of approved risk capital. |
| R07 | Authenticated Telegram approval is required for each proposed batch of new paper entries; position exits run automatically under predefined rules and generate notifications, while any reallocation into a new instrument requires a new approval. |
| R08 | AI must analyze timestamped global markets, global news/events, India-market context, and company/stock/ETF news before assessing tradeability and explaining candidates. It must cite supplied sources, return uncertainty/no-trade on missing/stale/conflicting inputs, and cannot override deterministic risk or approval controls. |
| R09 | AWS Mumbai (ap-south-1), Linux EC2, Docker Compose; no EKS, Kubernetes, or K3s. |
| R10 | Persistent state, audit trail, reconciliation, monitoring, backups, and tested recovery. |
| R11 | Missing approval, stale data, uncertain state, or critical dependency failure blocks entries. |
| R12 | Evaluate over at least 30 paper sessions against predefined criteria. |
| R13 | Verify costs and agree spending ceiling before paid services or provisioning. |
| R14 | Future live pilot is capped at INR 3,000 and requires staging, current broker/API verification, owner-approved risk limits, and separate go-live confirmation. |
| R15 | Before the Indian market opens, assess investability using current global markets, events, and stock/company news; the agent may recommend no trades. Revalidate market gates after open. |
| R16 | Rank eligible stocks and ETFs itself using verified inputs and the approved capital basis; determine a proposed position count within approved limits and explain selections and risks. |
| R17 | Require authenticated Telegram approval for each proposed entry batch; approved paper positions may exit automatically under predefined rules with a notification. Reusing freed capital for a new instrument requires a new approval. |
| R18 | AWS live-pilot schedule should start before India-market pre-open, perform analysis and notifications, and stop compute after close/reconciliation. Holiday-aware operation and overnight gap handling are required. |

At ₹50,000, planned per-trade risk is ₹250 and the daily threshold is ₹750. Loss accounting must include modeled costs and unrealized losses. Planned risk does not guarantee eventual loss magnitude.

### T04 — Daily loss accounting and short-lived swing position handling

The owner accepted the daily loss accounting and breaker-response rules below, including continuing existing position-specific exits without blanket liquidation. The strategy is now clarified as short-lived swing trading: brief positions, no forced same-day exit, and exit once a material profit is available rather than carrying the position indefinitely or forcing liquidation at the end of the trading day.

**Session loss accounting**

- Use the approved session risk capital frozen under T03; never increase it automatically. The daily loss threshold remains 1.5% of that approved amount (₹750 at ₹50,000 or ₹1,500 at ₹100,000).
- At the start of each exchange trading session, snapshot paper net liquidation value: simulator cash plus the marked value of open positions, less accrued simulated costs. Use the most recent valid official/available price for each position and include carried swing positions. This is the session baseline; overnight gaps are reflected as soon as a valid current-session price is available.
- Current net liquidation value uses the same cash-plus-marked-positions method. Session net P&L is current net liquidation value minus the session baseline. This includes realized and unrealized price P&L, and all modeled fees/taxes/slippage already reflected in cash or accrued costs. Do not double-count a closed position's P&L.
- Count the combined paper portfolio across all short-lived swing positions and instruments. Track daily P&L and entry locks by IST exchange trading session, not by UTC date or process uptime.
- If an open position has no valid mark, the system cannot calculate reliable loss/exposure: block new entries, alert, and retain protective exit management using the last valid state until reconciled.

**Daily loss breaker (owner accepted)**

- Trigger when session net P&L is less than or equal to negative 1.5% of the frozen approved session risk capital. The lock is sticky for the remainder of that exchange session even if P&L later recovers.
- On trigger, persist the lock, send an alert, cancel paper entry orders that are not filled, reject all new/replacement entries for the rest of the session, and invalidate any unfilled approval batch.
- Owner-approved: do not automatically liquidate every open position solely because the daily breaker fired. Continue each open paper position's already-authorized exit policy and send notifications. A separate position exit rule still executes normally.
- Reset the daily entry lock only at the next valid IST exchange session boundary, after a fresh baseline and state/data/position reconciliation. If state is uncertain, marks are stale, or reconciliation fails, keep entries blocked.
- This is a daily entry breaker, not a guarantee or hard cap on losses. Gaps, slippage, illiquidity, or unavailable markets can produce losses beyond the threshold, especially for overnight positions. No live orders or forced real-account actions are authorized.

**Short-lived swing position handling (owner clarification recorded)**

- Positions may remain open across exchange sessions; there is no forced end-of-day
  liquidation. They must not be held indefinitely. The intended horizon is brief,
  often around 2–3 sessions. The owner selected no fixed maximum holding age:
  positions exit only under the profit or protective rule.
- The owner selected a full-position exit at 2% net profit after modeled costs and
  a protective stop 2% below entry. The target depends on an approved fill-cost
  model; gaps can exceed the stop, and neither threshold guarantees an exit price.
- Carried positions remain subject to T03 exposure/risk limits and count in the
  next IST session's net-liquidation baseline. A position exit requires no new
  approval; reuse of freed capital for a new instrument does.
- When a trigger occurs outside exchange hours, simulate the exit at the first
  valid executable price under the eventual T10 fill model and disclose that a
  stop/profit price is not guaranteed. The loss breaker locks entries but does
  not itself force liquidation.

**Readiness:** Daily P&L measurement, the sticky 1.5% entry lock through the
exchange session, invalidation/cancellation of unfilled entries, reset only after
the next valid session's reconciliation, and no blanket position liquidation
solely because the breaker fires are owner-accepted. Short-lived swing, no
forced same-day liquidation, 2% net profit exit, 2% protective stop, and no fixed
age exit are owner-selected. Cost modeling, marks, gap execution, and recovery
targets still need resolution before a position-management runtime is enabled.

### T02 — First strategy (paper-only; short-lived swing rule clarified)

**Strategy:** Pre-open, market-regime-gated long-only trend-pullback continuation. Before the Indian market opens, the agent evaluates global markets/events and company/ETF news, decides whether the day is investable, ranks candidates, and sends a proposed entry batch sized within approved limits to Telegram. No entry is simulated until the owner approves that exact batch. Post-open market/price gates must still pass before paper entries. Position exits are automatic and notify the owner; deploying freed capital into another instrument requires a new approved batch.

This is a testable paper-strategy proposal, not a promise of profit or evidence of positive expectancy. Indicator thresholds are unvalidated hypotheses for historical/paper evaluation. No trading runtime is implemented by this task.

**Pre-open assessment and candidate selection**

- Before the exchange session, assemble a timestamped evidence bundle: prior Indian market/benchmark data, available global market indicators, scheduled India/global events, and fresh instrument/company/ETF news. Each material claim must retain its source and publication time.
- AI produces a structured market assessment (`FAVORABLE`, `UNFAVORABLE`, or `UNCERTAIN`) with cited evidence and a concise reason. Only `FAVORABLE` permits preparing an entry batch. Missing/stale sources, conflicting material reports, an unresolved high-impact event, or an `UNCERTAIN`/`UNFAVORABLE` assessment means report no trade. D14/T09 must verify the source set and define event severity/freshness before implementation; AI cannot bypass these gates.
- Candidate universe: exchange-qualified NSE/BSE cash-equity stocks and Groww-supported ETFs from the verified catalog. Use adjusted OHLCV where applicable, timestamps in IST, and no hard-coded shortlist. Long entries only; no short selling, leverage, derivatives, or averaging down.
- Use completed daily data for swing candidates.
- Rank only candidates with no unresolved material adverse instrument-specific news and with the style's technical setup below. Sort by descending cross-sectional percentile of trend strength ((EMA20 - EMA50) / ATR), then descending relative volume, then exchange and symbol. News is an evidence-based risk/context filter, not an unverified sentiment boost or standalone buy signal.
- Determine proposed count and share quantities only within approved simulated cash, 0.5% maximum planned risk per trade, and approved aggregate-risk, exposure, concentration, position-count, and order-frequency limits. If no candidates fit, report no trade. T03/T10 must resolve the limit and cost inputs; never infer missing limits as unlimited.
- Because v1 is paper-only, sizing uses approved simulated capital, not the live Groww account balance. Any read-only Groww balance integration remains a separate capability/scope decision in D13 and does not authorize real orders.

**Intraday profile (removed from approved scope)**

Intraday entries and forced same-session liquidation are not part of the current
strategy. The historical intraday parameters above have been removed from the
active specification; they must not be implemented or used for candidate ranking.

**Swing profile**

- Use completed daily bars; overnight holdings are permitted only under T04's approved policy.
- Proposed trend gate (unvalidated): instrument daily close > EMA(20) > EMA(50); NIFTY 50 daily close > EMA(20); instrument RSI(14) is 50–70.
- Trigger: one of the last three completed daily bars touches/crosses EMA(20) without closing below EMA(50); latest daily close is above the preceding day's high and volume is at least 1.2 times the median of the previous 20 completed daily bars.
- Entry: next exchange session open in simulation, only after batch approval; reject if the gap above signal close exceeds 0.5 x daily ATR(14), or if post-open risk/price checks fail.
- Initial stop: below the lowest low of the three-day pullback window by 0.1 x daily ATR(14); reject if stop is not below entry or distance exceeds 2 x daily ATR(14).
- The owner selected a full exit at 2% net profit after modeled costs and a
  protective stop 2% below entry, with no fixed maximum holding age. The 2%
  protective-stop reference in the technical watchlist is only relative to the
  last CSV close; actual exit evaluation requires a simulated entry fill and a
  cost model. Gaps can exceed trigger prices; fills are not guaranteed at a stop
  or target.

**Approval, sizing, automatic exit, and no-trade rules**

- Telegram proposal is created pre-open for a specific session and includes the market assessment, source links/timestamps, each instrument/exchange, rationale, entry trigger/price tolerance, stop, trailing/exit rules, quantity, capital allocation, estimated costs, and key risks. It expires at the configured time for that session; expiry must be decided in T05. Reject/timeout/invalid approval means no entries.
- Approval authorizes only the named batch and maximum paper quantities/capital. Recalculate risk at entry; material price, size, strategy, market-state, or risk-basis changes invalidate the affected approval. Post-open market regime deterioration, stale data, a risk limit/lock, or uncertain state blocks unfilled entries.
- Quantity = floor(approved per-trade risk budget / (entry-to-stop risk per share + estimated round-trip costs per share)), capped by approved available simulated cash and all T03 limits. Missing risk basis, prices, costs, limits, or valid quantity means no trade.
- Exits execute automatically according to the active deterministic position rules without a second trade approval; send an exit notification with reason, price, quantity, and simulated P&L. Telegram outage must not disable an already authorized protective exit; queue/retry its notification. An exit never authorizes a new entry: any reinvestment/rotation into another instrument requires a newly proposed and approved batch.
- No trade if the market assessment is not `FAVORABLE`; required evidence is stale/missing/conflicting; an unresolved high-impact event exists; benchmark trend gates fail; no instrument passes the setup; price/volume bars are invalid/incomplete; entry window/gap/tolerance fails; stop or quantity is invalid; risk/cash/exposure limits fail; approval is absent/expired; or a daily/recovery/safety lock is active.

**Owner clarification accepted:** The owner removed intraday as a primary strategy, kept only short-lived swing trading, and clarified that positions should be exited as soon as a material profit is available. The intended holding period is short-duration swing participation, not forced end-of-day liquidation and not indefinite holding. The final rule is to maximize profit from a favorable move while keeping the position brief and risk-managed.

**Readiness:** The earlier pre-open assessment, selection/sizing, Telegram approval, automatic exits, and reapproval before capital rotation remain accepted at the workflow level. The local CSV tool only produces a technical watchlist; it does not satisfy news/global-market gates or authorize trades. T09/D14 source/event verification, T05 approval expiry, and T10 fill assumptions remain prerequisites to execution. Strategy parameters are unvalidated and require historical/paper evaluation.

### T03 — Approved paper capital and exposure limits

These are paper-evaluation caps. The owner approved a maximum simulated-capital ceiling of ₹100,000 while retaining ₹50,000 as the default session amount. Limits are hard maxima, not targets or promises; the approved amount must be explicitly selected for each session. No live Groww balance, cash, holdings, or buying power is read or used.

| Limit | Approved value | At ₹50,000 default / ₹100,000 ceiling |
|---|---:|---:|
| Approved paper capital | Default ₹50,000; absolute ceiling ₹100,000 | ₹50,000 default / ₹100,000 maximum |
| Planned risk per new position | 0.5% of approved risk capital | ₹250 / ₹500 |
| Maximum aggregate open planned risk | 1.0% of approved risk capital | ₹500 / ₹1,000 |
| Daily loss entry lock | 1.5% of approved risk capital | ₹750 / ₹1,500 |
| Maximum gross invested exposure, including reserved entry orders | 80% of approved capital | ₹40,000 / ₹80,000 |
| Maximum exposure to one stock issuer or one ETF | 20% of approved capital | ₹10,000 / ₹20,000 |
| Maximum concurrent open positions | 5 | 5 |
| Maximum new entry intents per IST trading day | 5 | 5 |
| Borrowing, margin, and leverage | Not permitted | Cash-only simulation |

- Approved paper capital is frozen for the session, defaults to ₹50,000, and cannot exceed the owner-approved ₹100,000 ceiling. A session may approve any lower amount; choosing more than the default requires explicit session approval. It is never automatically derived from the Groww account balance.
- Size each position using T02's stop-distance/cost formula and the 0.5% per-position planned-risk ceiling. Apply the smallest applicable limit: risk budget, available simulated cash, 20% per-instrument/issuer allocation, 80% gross exposure, aggregate open risk, position count, and daily entry-intent count.
- Sum exposure and risk across all short-lived swing positions. Count same-issuer stocks on NSE and BSE together for issuer concentration. Count each ETF as one instrument; do not claim ETF underlying-issuer look-through unless verified holdings data is available. If required exposure or sizing data is missing, block the candidate.
- Include open positions and unfilled approved entry reservations in exposure/risk checks so simultaneous approvals cannot reuse the same capital. Permit at most one unresolved proposed/approved entry batch at a time; a new instrument after an exit requires a new Telegram approval as set in A12.
- The 5-entry limit counts each newly authorized entry intent per IST trading day, including re-entries and replacement instruments. Protective exits are not blocked by that limit. Retries of the same persistent intent are not new entries.
- T04 defines session net-liquidation accounting, unrealized P&L treatment, sticky entry lock and reset after reconciliation. Reaching the threshold blocks new entries; it does not authorize blanket liquidation or any live action.
- If approved capital changes, invalidate pending proposals and recompute limits before any further paper entry. Any increase above the ₹50,000 default requires explicit session approval; exceeding the ₹100,000 ceiling requires a separate owner decision.

**Consistency check:** At the ₹50,000 default, per-position risk is capped at ₹250, aggregate open risk at ₹500, daily loss lock at ₹750, gross exposure at ₹40,000, and per issuer/instrument exposure at ₹10,000. At the ₹100,000 ceiling, those amounts are ₹500, ₹1,000, ₹1,500, ₹80,000, and ₹20,000, respectively. Two positions each using the full per-position risk cap exhaust the aggregate open-risk cap. Four positions each at the per-issuer/instrument exposure maximum exhaust the gross exposure cap; a fifth position is possible only if other limits leave room. These are simultaneous maxima, not a recommendation to fill every slot.

**Readiness:** D02 is resolved by owner acceptance. The limits are paper-only and do not authorize live risk or execution.

### T01 — Initial instrument and style scope

- Previously accepted stock scope: all currently listed Indian cash-equity stocks on both NSE and BSE, including SME equity listings; do not constrain scanning to a hard-coded shortlist. A listing on each exchange is a distinct instrument, even when the ticker is shared.
- Allowed: all NSE/BSE-listed ETFs supported by Groww, including available categories, for the current short-lived swing style only. Actual categories, listing status, data access, and tradability must be verified before an instrument is used.
- Futures, options, indices, commodities, currencies, mutual funds, unlisted instruments, and other derivatives remain excluded unless separately specified and authorized.
- Owner selected profit/stop rules and no fixed age limit are recorded in A18. Entry hypotheses, cost-aware target calculation, and liquidity/eligibility filters remain open for T02/T04 and later data/risk tasks.
- `src/groww_agent/instruments.py` models NSE/BSE stocks and ETFs and fails closed when no catalog is loaded. It does not contain or fetch a complete listing catalog. T09 must verify permitted current sources and Groww availability; T18 must implement catalog ingestion before scanning the requested universe.

### Exclusions

Real orders, real capital allocation, autonomous limit/strategy changes, derivatives, leverage, short selling, multi-instance execution, and model training remain outside the currently authorized v1. The desired delivery sequence is paper first; any later live release requires a separate specification and explicit authorization. No profitability guarantee.

### Requested decision workflow (not yet implemented)

Send the independently ranked and sized proposed batch to the owner over Telegram before the Indian market opens. Approval authorizes only the listed paper entries. Manage resulting positions with predefined deterministic automatic exits and send an exit notification; do not require approval to protectively exit a position. Ask for approval again before reallocating freed capital to a new instrument. Missing/ambiguous/expired approval or unsafe state must not permit entry. Live execution remains separately gated.

## 3. Users and operating flow

The owner/operator decides limits, approves sessions, reviews results, and handles exceptions. The AI analyst explains shortlisted opportunities. An independent risk engine validates proposals. The simulator owns order state, while portfolio and operations components reconcile state and support recovery.

1. Validate configuration, exchange calendar, market/news data freshness, and service health.
2. Read the permitted account/capital information and reconcile persisted orders, positions, and cash; block entries if balance or state is unavailable or uncertain.
3. Assess whether conditions are suitable for trading; if not, report no trade.
4. Rank eligible stocks and ETFs using deterministic strategy rules and current verified inputs; AI may analyze/explain but cannot override controls.
5. Present the proposed paper-entry batch, rationale, risk, capital basis, limits, expiry, health, and carried positions through Telegram.
6. Authenticate and persist approval for that batch; independently validate risk and simulate only approved entries.
7. Manage open paper positions under predefined automatic exit rules; monitor loss, exposure, data, and service health.
8. Produce a daily report and consistent backup.

## 4. Risk and approval requirements

- Freeze the session risk-capital basis at approval; never increase it automatically.
- Require valid prices, sizing, and an exit policy before entry.
- Enforce funds, per-trade risk, aggregate risk, allocation, position-count, concentration, and order-frequency limits.
- Missing required limits block activation; they never imply unlimited permission.
- Persist approvals, configuration snapshots, entry locks, and kill-switch state across restarts.
- Use persistent intent identifiers and validated order-state transitions to prevent duplicates.
- Bind approval to one session, configuration, strategy version, capital, and expiry.
- Authenticate allowlisted Telegram identities; reject replayed, expired, and unauthorized actions.
- Material strategy, capital, or limit changes invalidate approval.
- AI output and session approval cannot override hard risk controls.
- Telegram failure blocks entries. Existing simulated positions follow predefined management rules.
- After recovery, reconcile state and validate authorization before allowing entries.
- Provide pause, kill switch, status, and a documented local administrative fallback.
- Use IST and an exchange-aware calendar for session boundaries; explicitly define overnight swing handling.

## 5. Architecture and reliability

Logical services: market data; scanner/strategy; AI analyst; independent risk engine; paper order manager; portfolio/reconciliation; Telegram; persistent database; monitoring/backups.

| Area | Baseline |
|---|---|
| Compute | One Linux EC2 instance, Mumbai, Docker Compose |
| Sizing | t4g.small candidate; validate capacity and compatibility |
| Persistence | EBS; SQLite candidate subject to concurrency/durability assessment |
| Backups | Protected S3 recovery copies; consistent snapshots and tested restoration |
| Monitoring | CloudWatch plus external heartbeat; data, database, disk, resource, and service health |
| Security | Protected secrets, least privilege, encrypted storage/backups, redacted logs |
| Scaling | Measure first; preserve an upgrade path without adding active/active execution |
| Shutdown | Only when position policy, reconciliation, reporting, and backups allow it |

A single EC2 instance supports recovery but cannot guarantee uninterrupted availability or survive all host/AZ outages without downtime. If stronger availability is required, revise architecture and budget before deployment.

| Failure | Required behavior |
|---|---|
| Process/EC2 restart | Restart automatically; validate and reconcile before resuming entries |
| Broker/data disconnect | Block entries, alert, enter safe mode |
| Stale/invalid data | Reject affected signals and entries |
| Unknown execution outcome | Reconcile before retrying; never assume failure |
| Database unavailable/disk full | Block new actions requiring durable state; alert |
| Telegram unavailable | Block entries; retain predefined position management |
| Daily breaker reached | Persist entry lock and alert |
| Host unreachable | External monitor detects missing heartbeat |
| Backup/restore failure | Alert; readiness gate remains unmet |

Recovery-time objective, recovery-point objective, stale-data threshold, heartbeat interval, alert deadline, retention, and acceptable outages remain to be agreed. Test restoration into a clean environment. For future live use, require immediate broker reconciliation and a manual Groww position-management procedure.

## 6. Simulation and evaluation

Model charges/taxes, slippage, liquidity assumptions, partial fills, rejects, cancellations, gaps, delayed responses, market sessions, and overnight positions. Track cash, exposure, drawdown, and realized/unrealized P&L. Clearly label all results as simulated and disclose assumptions and data gaps.

Freeze evaluation criteria before starting at least 30 paper sessions. Completion does not authorize live trading. Record invalid/missing sessions, incidents, costs, strategy/configuration changes, and unresolved defects.

## 7. Cost constraints

| Category | Historical planning allowance |
|---|---:|
| Recoverable single-instance AWS v1 | ₹1,500–₹2,500/month |
| AI usage | ₹200–₹500/month |
| Groww/API/data subscriptions | Separate; unconfirmed |
| Future more robust setup | ₹4,000–₹7,000/month |
| Future Multi-AZ setup | ₹7,000–₹12,000+/month |

These are inherited estimates, not current quotes or spending approval. Verify taxes, networking/public IP, storage, logs, backup, monitoring, and subscriptions. No EKS, GPU, or unnecessary managed services. Avoid NAT Gateway unless a verified need justifies it. Cache/batch AI calls and enforce application quotas. Set retention and forecast/budget alerts; alerts are not spending caps. Do not sacrifice monitoring or recovery for shutdown savings. If the reliable design exceeds budget, remain local or revise the plan.

## 8. Open decisions

| ID | Decision | Required before |
|---|---|---|
| D01 | Strategy rules, short-lived swing universe and allocation | Candidate strategy recorded in T02; deterministic exits and evaluation required before implementation |
| D02 | Capital ceiling, allocation, position count, concentration, aggregate risk, order frequency | Resolved in T03; implementation remains downstream |
| D03 | Daily baseline/reset, unrealized loss, overnight treatment, breaker exit policy | Proposed in T04; owner acceptance required before risk implementation |
| D04 | Telegram identities, expiry, reapproval after recovery, fallback controls | Approval implementation |
| D05 | Data source, Groww capabilities/authentication, restrictions, subscriptions | Integration implementation |
| D06 | Fill model, costs, slippage, liquidity, validation examples | Simulator implementation |
| D07 | Recovery targets, retention, freshness/heartbeat/alert thresholds | Operations implementation |
| D08 | Overnight monitoring and safe shutdown rules | Proposed in T04; owner acceptance required before scheduling implementation |
| D09 | AWS ceiling, AI cap, subscriptions, taxes, budget escalation | Paid services/provisioning |
| D10 | Evaluation metrics, thresholds, critical-defect criteria | Paper evaluation |
| D11 | ETF types, listing exchanges, and exclusions | Confirmed in T01; verify listings/data/broker availability in T09 |
| D12 | Paper-first versus live-trading release sequence; real-order authorization and controls | Paper first confirmed; any live integration or execution requires separate specification and authorization |
| D13 | Groww account data scope (available cash, holdings, permissions) and approved capital source | Account integration and risk implementation |
| D14 | News/global-event sources, freshness, coverage, cost, and how they inform—but cannot override—deterministic controls | Strategy and market-analysis implementation |
| D15 | Telegram approval granularity and expiry; which approved positions may be sold automatically and under what predefined exit rules | Batch-level entry approval and automatic predefined exits confirmed; exact policy required before implementation |
| D16 | Measurable return/risk objective; no guaranteed profit or loss minimization | Strategy and evaluation criteria |

## 9. Tracking rules

Statuses: Pending; In progress; Blocked (name blocker); Review; Done (acceptance evidence recorded); Deferred (explicit scope decision).

Keep stable task IDs. Work on one active task at a time unless agreed otherwise. Start only after dependencies and authorization are satisfied. Update status, dashboard counts, completion log, decisions, and next task together. A feature is Done only when all required tasks are Done. Discussion or planning does not complete implementation tasks. Record scope changes rather than silently changing limits. The owner accepts material requirement decisions; technical completion needs evidence against acceptance criteria.

## 10. Feature backlog and user stories

### F01 — Requirements and decisions

As the owner, I want explicit strategies, limits, and operating rules so the agent cannot fill gaps with unsafe assumptions.

| ID | Task | Acceptance criteria | Dependencies | Status |
|---|---|---|---|---|
| T01 | Define instruments and trading styles | Stocks, ETF categories, short-lived swing scope, and exclusions recorded and accepted | — | Done |
| T02 | Define first strategy | Entry, material-profit exit, stop, maximum holding age, sizing inputs, timeframe, no-trade rules unambiguous | T01 | Review |
| T03 | Set capital/exposure limits | D02 resolved; all required limits specified | T01 | Done |
| T04 | Define loss/overnight rules | D03/D08 resolved, including breaker and short-lived swing handling | T02–T03 | Review |
| T05 | Define session approval rules | D04 resolved, including expiry and recovery | T03–T04 | Pending |
| T06 | Set recovery/health targets | D07 resolved with measurable thresholds | — | Pending |
| T07 | Set spending limits | D09 resolved; paid services remain gated | — | Pending |
| T08 | Set evaluation criteria and approve baseline | D10 resolved; baseline accepted; blockers recorded | T01–T07 | Pending |

### F02 — Integration validation and design

As the operator, I want verified capabilities and a clear design before implementation.

| ID | Task | Acceptance criteria | Dependencies | Status |
|---|---|---|---|---|
| T09 | Verify Groww/data capabilities | D05 resolved using current official documentation; limitations recorded | T01 | Pending |
| T10 | Specify simulation assumptions | D06 resolved with worked examples | T02, T09 | Pending |
| T11 | Define component interfaces | Inputs, outputs, failures, ownership documented | T08–T10 | Review |
| T12 | Define state/security design | Order states, approvals, audit data, secrets, backup boundaries documented | T11 | Review |
| T13 | Review implementation readiness | Blocking decisions resolved; separate implementation instruction recorded | T12 | Blocked (T08–T10 data/source and simulation verification) |

### F03 — Local foundation and persistence

As the operator, I want a reliable local paper system that preserves state.

| ID | Task | Acceptance criteria | Dependencies | Status |
|---|---|---|---|---|
| T14 | Create authorized project foundation | Local startup works; paper mode enforced; config validates; repository scaffold already created, runtime criteria outstanding | T13 | Done (foundation scope explicitly authorized) |
| T15 | Implement persistent records | Sessions, signals, intents, orders, fills, positions persist | T14 | Done (SQLite record layer only) |
| T16 | Add audit/secrets handling | Timestamped identified actions; no secrets in logs | T15 | Review |
| T17 | Verify restart behavior | State survives restart; entries blocked until validation | T16 | Review |

### F04 — Market data and scanning

As a paper trader, I want trustworthy data and reproducible scans.

| ID | Task | Acceptance criteria | Dependencies | Status |
|---|---|---|---|---|
| T18 | Implement data adapter | Agreed instruments/timestamps normalize correctly | T09, T14 | Review (local CSV only) |
| T19 | Validate freshness/integrity | Stale, missing, invalid, out-of-order data handled as specified | T18 | Review (OHLCV validation; freshness/calendar pending) |
| T20 | Add calendar/session handling | IST sessions/holidays match agreed calendar | T18 | Pending |
| T21 | Implement scanner | Same inputs yield same shortlist; exclusions enforced | T19–T20 | Review (technical watchlist; catalog exclusions pending) |

### F05 — Strategy and AI analysis

As the owner, I want explainable signals, reproducible rules, and controlled AI usage.

| ID | Task | Acceptance criteria | Dependencies | Status |
|---|---|---|---|---|
| T22 | Implement first strategy | Entry/exit/no-trade examples yield expected signals | T02, T21 | Review (unvalidated technical rules; no trade authorization) |
| T23 | Add AI explanations | Uses supplied data; invalid/missing AI output cannot authorize orders | T22 | Pending |
| T24 | Add AI usage controls | Calls, retries, caching, spend quota enforced | T07, T23 | Pending |

### F06 — Independent risk controls

As the owner, I want every proposed trade checked independently against approved limits.

| ID | Task | Acceptance criteria | Dependencies | Status |
|---|---|---|---|---|
| T25 | Add sizing/capital checks | Funds, stop distance, risk, capital pass boundary checks | T03, T15, T22 | Pending |
| T26 | Add exposure checks | Position, concentration, aggregate-risk breaches rejected | T25 | Pending |
| T27 | Add daily breaker | Agreed loss accounting triggers persistent lock at threshold | T04, T26 | Pending |
| T28 | Add pause/kill switch | Entries stop; locks survive restart; positions follow policy | T27 | Pending |
| T29 | Verify fail-closed controls | Missing approval, stale data, invalid config, uncertain state block entries | T17, T19, T28 | Pending |

### F07 — Paper execution and portfolio

As a paper trader, I want realistic simulated execution and accurate portfolio accounting.

| ID | Task | Acceptance criteria | Dependencies | Status |
|---|---|---|---|---|
| T30 | Implement order lifecycle | States/transitions match design | T10, T15, T25 | Pending |
| T31 | Add fill/cost model | Charges, slippage, partial fills, rejects, cancellations match examples | T30 | Pending |
| T32 | Add portfolio accounting | Cash, positions, fees, realized/unrealized P&L reconcile | T31 | Pending |
| T33 | Add idempotency/reconciliation | Repeats produce no duplicate fills; restart/unknown outcomes reconcile | T17, T32 | Pending |
| T34 | Verify paper isolation | No real-order path; live execution credentials unnecessary | T29, T33 | Pending |

### F08 — Telegram approvals and controls

As the owner, I want to approve each session and control the agent through Telegram.

| ID | Task | Acceptance criteria | Dependencies | Status |
|---|---|---|---|---|
| T35 | Authenticate operator actions | Unauthorized identities and replays rejected | T05, T16 | Pending |
| T36 | Add session approval | Approval binds session, capital, limits, strategy version, expiry | T35 | Pending |
| T37 | Connect pause/stop/status | Controls affect/report correct persistent state | T28, T36 | Pending |
| T38 | Handle Telegram outage | Entries stop; positions follow policy; recovery audited | T37 | Pending |

### F09 — Reporting, monitoring, recovery

As the operator, I want visible health and recoverable state so failures are detected and handled.

| ID | Task | Acceptance criteria | Dependencies | Status |
|---|---|---|---|---|
| T39 | Add daily paper report | Labeled simulated P&L/costs/exposure/rejects/incidents reconcile | T24, T32, T36 | Pending |
| T40 | Add health checks/alerts | Agreed service/data/storage/heartbeat failures detected within targets | T06, T38 | Pending |
| T41 | Add backup/restore | Consistent backup restores cleanly within targets | T06, T33 | Pending |
| T42 | Write recovery/shutdown procedures | Restart, restore, outage, shutdown steps executable/reviewed | T40–T41 | Pending |
| T43 | Run failure scenarios | Crash, disconnect, stale data, database failure, uncertain execution meet targets | T34, T38, T42 | Pending |

### F10 — Optional AWS paper deployment

As the owner, I want a measured-cost deployment after local reliability is demonstrated.

| ID | Task | Acceptance criteria | Dependencies | Status |
|---|---|---|---|---|
| T44 | Review deployment/current costs | Sizing, storage, networking, monitoring, backup, subscriptions fit budget | T07, T43 | Pending |
| T45 | Record provisioning authorization | Explicit instruction before paid resource creation | T44 | Pending |
| T46 | Deploy paper services | Mumbai EC2/Compose work with protected state/secrets | T45 | Pending |
| T47 | Verify cloud operations | External/cost alerts, restart, restore, scheduling pass | T46 | Pending |

### F11 — Evaluation and MVP review

As the owner, I want evidence of strategy behavior, reliability, and cost before the next decision.

| ID | Task | Acceptance criteria | Dependencies | Status |
|---|---|---|---|---|
| T48 | Start controlled evaluation | Approved config and evaluation criteria frozen/recorded | T08, T39, T43; T47 if cloud | Pending |
| T49 | Complete 30+ paper sessions | Reports/incidents recorded; invalid/missing sessions identified | T48 | Pending |
| T50 | Assess results/defects | Performance, drawdown, costs, reliability, control failures assessed against preset criteria | T49 | Pending |
| T51 | Complete MVP review | Accept, extend, or revise documented; no automatic live enablement | T50 | Pending |

## 11. Milestones and overall acceptance

| Milestone | Tasks | Gate | Status |
|---|---|---|---|
| M0 Requirements agreed | T01–T08 | Scope, limits, budget, targets accepted | Pending |
| M1 Design ready | T09–T13 | Integrations verified; implementation authorized | Pending |
| M2 Local paper MVP | T14–T38 | Complete paper workflow with independent controls | Pending |
| M3 Operational readiness | T39–T43 | Reports, recovery, failure scenarios pass | Pending |
| M4 Optional cloud readiness | T44–T47 | Separate authorization and cloud checks complete | Pending |
| M5 MVP evaluated | T48–T51 | Evidence reviewed; next decision recorded | Pending |

Overall acceptance: zero real orders/fund movements; every entry traceable to session approval, strategy output, and risk approval; rejected actions have reasons; control boundaries verified; no duplicate execution after recovery; clean restore within targets; approved cost budget met; no unresolved critical control/reliability defects. Optional cloud tasks may be explicitly Deferred for a local evaluation; record that decision.

## 12. Completion log

| Task | Date recorded | Result | Validation/evidence | Remaining issues |
|---|---|---|---|---|
| T01 | 8 November 2026 | Owner confirmed all currently listed stocks and all Groww-supported ETFs on NSE and BSE; current approved strategy is short-lived swing, not intraday. No fixed shortlist. | Unit tests verify both-exchange scope, exchange-qualified duplicate tickers, ETF support, swing-only style, exclusions, and fail-closed catalog behavior. | Verify listing, data, and broker availability in T09 and implement catalog ingestion in T18. |
| T02 (Review) | 8 November 2026 | Owner clarified short-lived swing: positions may cross sessions, no forced close-of-day liquidation, full exit at 2% net profit after modeled costs, protective stop 2% below entry, and no fixed maximum age. | Workflow and entry hypotheses are documented; local CSV scanning is technical-watchlist-only, with no runtime trade behavior or performance claim. | Entry rules remain unvalidated; costs, gaps, catalog/news gates, approval and position management are still required. |
| T03 | 8 November 2026 | Owner approved a ₹100,000 maximum paper-capital ceiling, retaining ₹50,000 as the default session amount, and accepted all proposed risk/exposure limits. | Approved percentages and amounts at both the default and ceiling are documented in the T03 section; arithmetic and task-status checks pass. No runtime enforcement implemented. | T04 documents daily-loss accounting/reset and short-lived swing handling; persistent enforcement remains unimplemented. |
| T04 (Review) | 8 November 2026 | Owner accepted daily net-liquidation P&L measurement and a sticky 1.5% entry lock, and selected a 2% net-profit target, 2% protective stop, and no maximum age. No blanket liquidation solely from the breaker. | Fill-derived portfolio snapshot now exists; the daily baseline and breaker are not persistently enforced. | Verified marks, cost/gap model, IST calendar and recovery behavior remain prerequisites. |
| T11/T12 (Review) | 8 November 2026 | Documented logical component contracts, paper-only order boundary, state/event responsibilities, trust boundaries, and recovery/failure behavior in the HLD. | Architecture documentation updated; initial SQLite schema and record layer implemented under T15, but no production security, migration, or backup validation. | Review contracts against T08–T10 provider/strategy/simulation decisions and revise persistence/backup design as needed. |
| T14 | 8 November 2026 | Added validated local paper-only startup/configuration CLI and SQLite schema initialization, proceeding on the owner's explicit local implementation instruction while full readiness remains blocked. | `config-check`, `start`, and `status` smoke-tested; live mode is rejected before database creation; 19 unit tests pass. | Foundation deliberately disables entries; this is not a running strategy/trading service and does not satisfy full T13 readiness. |
| T15 (partial) | 8 November 2026 | Added a fill-based, long-only paper ledger snapshot for cash, fees, realized/unrealized P&L, and net liquidation when marks are supplied. Missing marks make net liquidation unavailable. | End-to-end SQLite fill examples validate buy/sell cost basis and P&L; missing marks fail closed for valuation. | The complete T32 acceptance criteria still require a fill simulator/cost model, persisted marks, position reconciliation, and daily-baseline integration. |
| T16/T17 (Review) | 8 November 2026 | Added timestamped audit persistence with common secret-assignment/Bearer redaction; restart tests confirm stored records persist and CLI never enables entry processing. | Unit tests exercise redaction, persistence and always-disabled startup behavior. | Redaction is not a full secret-management system; recovery validation and conditional entry enabling do not exist. |

## 13. Decision log

| ID | Decision | State |
|---|---|---|
| A01 | Development/staging is paper/read-only; future live pilot is separate | No live order path in current implementation; live pilot requires separate go-live confirmation. |
| A02 | AWS Mumbai EC2 + Docker Compose; no Kubernetes/EKS | Proposed baseline; current phase is cost plan only, no provisioning authorization. |
| A03 | ₹50,000 default simulated capital; 0.5% per-trade risk; 1.5% daily breaker | Confirmed; maximum simulated-capital ceiling ₹100,000 and other T03 limits owner-approved. |
| A04 | Telegram approval | Confirmed: authenticate approval per pre-open proposed entry batch; paper exits are automatic under predefined rules with an exit notification. Reapproval is required before allocating freed capital to a new instrument. Expiry remains unresolved. |
| A05 | Live release is separate gated phase | Owner wants a maximum INR 3,000 Groww pilot only after staging and a separate explicit go-live confirmation. |
| A06 | Create local Git repository for future source code and Terraform | Authorized 7 November 2026; scaffold created; no application/runtime or deployable resources implemented |
| A07 | Publish scaffold privately to GitHub; keep all local repositories inside current workspace | Authorized 8 November 2026; publication pending verification |
| A08 | Initial instrument universe | Confirmed: all currently listed cash-equity stocks plus all NSE/BSE-listed ETFs supported by Groww; current approved style is short-lived swing trading, not intraday. |
| A09 | Desired product workflow | Agent assesses market conditions pre-open, uses news/global-event information, independently ranks stock/ETF candidates using an approved paper-capital basis, and may recommend no trades. No guaranteed outcome. |
| A10 | Delivery and execution gate | Paper/read-only staging first; future live release requires evaluation, current broker verification, approved limits, and a separate explicit go-live confirmation. |
| A11 | ETF universe | All NSE/BSE-listed ETFs supported by Groww are desired candidates, across available categories; instrument availability and risk checks remain mandatory. |
| A12 | Entry approval and selection | Agent ranks/sizes a pre-open batch; owner approves that batch before entries. Exits run automatically under predefined deterministic rules and notify the owner; reallocation requires a new approval. Approval transport/authentication remains unimplemented. |
| A13 | Selection objective | Seek attractive risk-adjusted opportunities using market/news/event information; the system may recommend no trades and cannot guarantee profit or minimize all losses. |
| A14 | First strategy | The owner clarified short-lived swing trading: brief positions, no forced same-day exit, and a profit-taking exit when an approved material-gain condition is reached. Intraday is not the approved baseline; selected thresholds are in A18. |
| A15 | Paper capital and exposure limits | Owner-approved: ₹50,000 default session capital; ₹100,000 maximum ceiling; 0.5% risk per position; 1% aggregate open risk; 1.5% daily loss entry lock; 80% gross exposure; 20% per issuer/instrument; five open positions; five new entries per IST day; no leverage. |
| A16 | Daily loss behavior | Owner accepted session net-liquidation P&L including realized/unrealized results and costs; sticky entry lock until next valid exchange session after reconciliation; continue position-specific exits without forced liquidation solely from breaker. |
| A17 | Holding horizon | Brief swing holding across sessions is allowed with no forced close-of-day exit. A few sessions (often 2–3) is guidance; owner selected no hard time cutoff, with exit only by the A18 profit/protective rules. |
| A18 | Owner-selected swing exits | Full position exit at 2% net profit after modeled costs; protective stop at 2% below entry; no fixed maximum holding age. Fill-cost model and gap handling remain unresolved. |
| A19 | Data-provider direction | Local CSV is for development only. Future Groww integration requires verifying active API subscription terms, account permissions, market-data coverage and order behavior; no subscription or credentials authorized yet. |
| A20 | AWS daily runtime | Owner accepted EC2 schedule design: start 08:15 IST before pre-open, validate/reconcile, stop after close and clean shutdown. Use Asia/Kolkata scheduling plus exchange-holiday checks; owner accepts overnight gap risk. |
| A21 | Live pilot risk limits | Owner accepted these for staging design only: INR 3,000 capital cap, INR 15 planned risk/position, INR 45 daily entry lock, INR 2,400 gross exposure, INR 600 per instrument, one open position, and at most one new entry/session. No live-order authorization. |
| A22 | AWS budget alert | Owner selected INR 1,000/month budget alert threshold for later deployment planning. AWS Budgets is not a hard spend cap; no provisioning authorization. |

## 14. Change log

| Date | Change |
|---|---|
| 7 November 2026 | Created persistent master document from the planning specification and 51-task backlog. All delivery tasks remain Pending. |
| 7 November 2026 | Created local `groww-ai-trading-agent/` Git repository scaffold with source, tests, Compose, Terraform, documentation, and ignore rules. T14 remains Pending because runtime acceptance criteria and prerequisite gates are outstanding. No remote, AWS resources, or trades created. |
| 8 November 2026 | Moved the authoritative tracker into `docs/WORK-TRACKER.md` for portability, replaced the original external document with a link, and updated repository references. Private GitHub publication authorized; not yet verified. All 51 delivery tasks remain Pending. |
| 8 November 2026 | Updated T01 per owner direction to cover all currently listed cash equities on NSE and BSE, not a 21-symbol seed list. The domain model requires exchange-qualified listings and fails closed without a loaded catalog; full source verification and ingestion remain T09/T18. Installed Python 3.12.10 for the current Windows user and created/installed the project in its ignored `.venv`; unit tests pass. |
| 8 November 2026 | Recorded the owner's desired product: news/global-event analysis, Groww account balance, stocks and ETFs, Telegram batch approval for proposed entries, and automatic exits under predefined rules. Confirmed paper-first delivery and all Groww-supported NSE/BSE ETFs; updated T01 model. Account access and live execution remain gated by separate specification/authorization. |
| 8 November 2026 | Drafted and revised T02 to match the owner's pre-open news/global-market assessment, proposed/sized entry batch, Telegram approval, automatic exits with notification, and reapproval before capital rotation. The technical trend-pullback profiles and fail-closed gates are unvalidated hypotheses. Marked T02 Review; no runtime strategy code was added. |
| 8 November 2026 | Owner accepted the revised T02 workflow and strategy proposal. Marked T02 Done; no runtime strategy code, live Groww access, or real trading was authorized. |
| 8 November 2026 | Drafted T03 proposed paper-capital, allocation, aggregate-risk, exposure, concentration, position-count, and entry-frequency limits. Marked T03 Review pending owner approval; no runtime risk enforcement implemented. |
| 8 November 2026 | Owner approved T03 limits, increasing the paper-capital ceiling to ₹100,000 while retaining ₹50,000 as the default session amount and accepting the proposed percentages/counts. Marked T03 Done; no runtime risk enforcement or live-account access was authorized. |
| 8 November 2026 | Owner accepted T04's daily loss measurement and sticky entry-lock behavior and requested no blanket position liquidation at the breaker. The owner also revised T02 toward swing-only analysis with intraday-style exits; overnight/holding period is ambiguous, so T02 and T04 are reopened for clarification. |
| 8 November 2026 | Drafted T04 loss accounting, sticky daily entry-breaker, and overnight swing policy, including a recommendation to manage existing positions by their approved exits rather than force-liquidate solely because the daily breaker fires. Marked T04 Review pending owner acceptance. |
| 8 November 2026 | Owner clarified short-lived swing: positions may cross sessions, there is no forced end-of-day liquidation, and exits should capture a material favorable move without indefinite holding. A few sessions (often 2–3) is guidance, not a numeric maximum. Reconciled tracker and architecture to remove intraday as the active profile; exact profit/stop/maximum-age rules remain open. |
| 8 November 2026 | Expanded the HLD with paper-only component responsibilities and flows, logical state/order lifecycle, ledger and breaker behavior, trust boundaries, recovery/failure policy, and design gates. T11/T12 moved to Review; T13 is blocked pending prerequisites and separate implementation authorization. No runtime or deployment was implemented. |
| 8 November 2026 | Owner explicitly authorized local paper-only implementation. Added a CLI with validated configuration and safe startup/status, plus a SQLite state store for core records, audit redaction, basic paper-order transitions and idempotent fill/intent persistence. T14/T15 completed for this limited scope; T16/T17 remain Review. No strategy, broker, Telegram, market-data or live execution path exists. |
| 8 November 2026 | Follow-up implementation adds schema-v2 recovery state that locks entries on every start, an additive v1 database migration, and a fill-derived portfolio snapshot accounting for cash, fees, realized/unrealized P&L, and missing marks. Twenty-three unit tests pass; T16/T17 remain Review and portfolio work does not complete T32. |
| 8 November 2026 | Owner selected 2% net-profit exit, 2% protective stop, no fixed maximum holding age, and local CSV input. Added OHLCV CSV validation and a deterministic technical watchlist using the documented swing hypotheses. It is explicitly watchlist-only and does not create proposals or orders. Twenty-nine unit tests pass. |
| 8 November 2026 | Owner clarified desired destination: AWS-hosted Groww live pilot capped at INR 3,000 after staging and a separate go-live confirmation. Current authorization is plan only. Added a cost/schedule/gate proposal; no AWS resources, Groww subscription, credentials, or live orders used. |
| 8 November 2026 | Owner accepted the proposed INR 3,000 pilot limits for staging design only, the INR 1,000/month AWS Budget alert threshold, and stopping EC2 at 16:00 IST while accepting overnight gap risk. This is not provisioning or live-order authorization. |

## 15. Next work session

Continue read-only/staging implementation and official Groww API verification. Use [aws-live-pilot-plan.md](./aws-live-pilot-plan.md) as the current schedule/cost/risk baseline. AWS provisioning, paid subscriptions, credential collection/use, and real orders remain unauthorized until separately approved.

When resuming in another chat, read this document first and carry forward its current task states and decisions. Updates occur while we work together; this document does not run background work or monitoring.
