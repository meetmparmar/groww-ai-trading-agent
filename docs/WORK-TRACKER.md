# Groww AI Trading Agent — Requirements and Work Tracker

Version: 1.1 | Created: 7 November 2026 | Last updated: 8 November 2026

## Project dashboard

- Stage: Requirements gathering; planning only.
- Requirements and backlog: Drafted and saved; decisions awaiting confirmation.
- Backlog: 51 tasks; 0 Done, 0 In progress, 51 Pending.
- Next eligible task: T01 — Define instruments and trading styles.
- Repository: Local Git scaffold created at `groww-ai-trading-agent/`; application code not implemented.
- AWS resources: Not provisioned.
- Real trading: Not authorized.

This is the master work document. Update it after each task or material decision. Documentation creation is complete but does not count as completion of any of the 51 delivery tasks.

## 1. Purpose and authorization

Build an AI-assisted Indian-equity trading agent using Groww as the intended broker integration. It will scan instruments, apply versioned strategies, explain opportunities, enforce independent risk controls, simulate orders, and report through Telegram.

Current authorization covers planning, maintaining this document, creating the local source-code/infrastructure repository scaffold, and publishing that scaffold to a private GitHub repository. All local repositories must remain within the current workspace. Application behavior, deployable infrastructure implementation, AWS provisioning, paid subscriptions, and trade execution remain outside current authorization. Later implementation requires a separate instruction. No task below constitutes authorization by itself.

Source: the referenced “Refine Trading Agent Prompt” conversation and the planning specification and requirements backlog in this chat. Historical estimates are retained as planning inputs, not current quotations.

## 2. Confirmed requirements

| ID | Requirement |
|---|---|
| R01 | Paper-trading-only v1; simulated funds and orders; no live-order path. |
| R02 | Groww is the intended integration; verify current API/data capabilities and restrictions. |
| R03 | Intraday and swing equities are in scope; exact strategies and universe remain open. |
| R04 | Default simulated capital: ₹50,000, subject to session approval. |
| R05 | Maximum planned risk per trade: 0.5% of approved risk capital. |
| R06 | Daily loss circuit breaker: 1.5% of approved risk capital. |
| R07 | Authenticated Telegram approval once per session before new simulated entries. |
| R08 | AI explains and analyzes; deterministic controls govern risk and execution. |
| R09 | AWS Mumbai (ap-south-1), Linux EC2, Docker Compose; no EKS, Kubernetes, or K3s. |
| R10 | Persistent state, audit trail, reconciliation, monitoring, backups, and tested recovery. |
| R11 | Missing approval, stale data, uncertain state, or critical dependency failure blocks entries. |
| R12 | Evaluate over at least 30 paper sessions against predefined criteria. |
| R13 | Verify costs and agree spending ceiling before paid services or provisioning. |
| R14 | Live trading needs a separate specification, current compliance/broker verification, and authorization. |

At ₹50,000, planned per-trade risk is ₹250 and the daily threshold is ₹750. Loss accounting must include modeled costs and unrealized losses. Planned risk does not guarantee eventual loss magnitude.

### Exclusions

Real orders, real capital allocation, autonomous limit/strategy changes, derivatives, leverage, short selling, multi-instance execution, and model training are outside v1. Revisit exclusions only through an explicit scope decision. No profitability guarantee.

## 3. Users and operating flow

The owner/operator decides limits, approves sessions, reviews results, and handles exceptions. The AI analyst explains shortlisted opportunities. An independent risk engine validates proposals. The simulator owns order state, while portfolio and operations components reconcile state and support recovery.

1. Validate configuration, calendar, data, and service health.
2. Reconcile orders, positions, and cash.
3. Present paper mode, session, strategy version, capital, limits, expiry, health, and carried positions through Telegram.
4. Authenticate and persist session approval.
5. Scan and evaluate deterministic strategy rules; add AI explanations where useful.
6. Independently validate risk, then simulate authorized orders.
7. Monitor positions, loss, exposure, data, and system health.
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
| D01 | Strategy rules, universe, intraday/swing allocation | Strategy implementation |
| D02 | Capital ceiling, allocation, position count, concentration, aggregate risk, order frequency | Risk implementation |
| D03 | Daily baseline/reset, unrealized loss, overnight treatment, breaker exit policy | Risk implementation |
| D04 | Telegram identities, expiry, reapproval after recovery, fallback controls | Approval implementation |
| D05 | Data source, Groww capabilities/authentication, restrictions, subscriptions | Integration implementation |
| D06 | Fill model, costs, slippage, liquidity, validation examples | Simulator implementation |
| D07 | Recovery targets, retention, freshness/heartbeat/alert thresholds | Operations implementation |
| D08 | Overnight monitoring and safe shutdown rules | Scheduling implementation |
| D09 | AWS ceiling, AI cap, subscriptions, taxes, budget escalation | Paid services/provisioning |
| D10 | Evaluation metrics, thresholds, critical-defect criteria | Paper evaluation |

## 9. Tracking rules

Statuses: Pending; In progress; Blocked (name blocker); Review; Done (acceptance evidence recorded); Deferred (explicit scope decision).

Keep stable task IDs. Work on one active task at a time unless agreed otherwise. Start only after dependencies and authorization are satisfied. Update status, dashboard counts, completion log, decisions, and next task together. A feature is Done only when all required tasks are Done. Discussion or planning does not complete implementation tasks. Record scope changes rather than silently changing limits. The owner accepts material requirement decisions; technical completion needs evidence against acceptance criteria.

## 10. Feature backlog and user stories

### F01 — Requirements and decisions

As the owner, I want explicit strategies, limits, and operating rules so the agent cannot fill gaps with unsafe assumptions.

| ID | Task | Acceptance criteria | Dependencies | Status |
|---|---|---|---|---|
| T01 | Define instruments and trading styles | Universe, allowed instruments, intraday/swing scope, exclusions recorded | — | Pending |
| T02 | Define first strategy | Entry, exit, stop, sizing inputs, timeframe, no-trade rules unambiguous | T01 | Pending |
| T03 | Set capital/exposure limits | D02 resolved; all required limits specified | T01 | Pending |
| T04 | Define loss/overnight rules | D03/D08 resolved, including breaker and swing handling | T02–T03 | Pending |
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
| T11 | Define component interfaces | Inputs, outputs, failures, ownership documented | T08–T10 | Pending |
| T12 | Define state/security design | Order states, approvals, audit data, secrets, backup boundaries documented | T11 | Pending |
| T13 | Review implementation readiness | Blocking decisions resolved; separate implementation instruction recorded | T12 | Pending |

### F03 — Local foundation and persistence

As the operator, I want a reliable local paper system that preserves state.

| ID | Task | Acceptance criteria | Dependencies | Status |
|---|---|---|---|---|
| T14 | Create authorized project foundation | Local startup works; paper mode enforced; config validates; repository scaffold already created, runtime criteria outstanding | T13 | Pending |
| T15 | Implement persistent records | Sessions, signals, intents, orders, fills, positions persist | T14 | Pending |
| T16 | Add audit/secrets handling | Timestamped identified actions; no secrets in logs | T15 | Pending |
| T17 | Verify restart behavior | State survives restart; entries blocked until validation | T16 | Pending |

### F04 — Market data and scanning

As a paper trader, I want trustworthy data and reproducible scans.

| ID | Task | Acceptance criteria | Dependencies | Status |
|---|---|---|---|---|
| T18 | Implement data adapter | Agreed instruments/timestamps normalize correctly | T09, T14 | Pending |
| T19 | Validate freshness/integrity | Stale, missing, invalid, out-of-order data handled as specified | T18 | Pending |
| T20 | Add calendar/session handling | IST sessions/holidays match agreed calendar | T18 | Pending |
| T21 | Implement scanner | Same inputs yield same shortlist; exclusions enforced | T19–T20 | Pending |

### F05 — Strategy and AI analysis

As the owner, I want explainable signals, reproducible rules, and controlled AI usage.

| ID | Task | Acceptance criteria | Dependencies | Status |
|---|---|---|---|---|
| T22 | Implement first strategy | Entry/exit/no-trade examples yield expected signals | T02, T21 | Pending |
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

No delivery tasks completed yet.

| Task | Completed date | Result | Validation/evidence | Remaining issues |
|---|---|---|---|---|
| — | — | — | — | — |

## 13. Decision log

| ID | Decision | State |
|---|---|---|
| A01 | v1 is paper trading only | Confirmed baseline |
| A02 | AWS Mumbai EC2 + Docker Compose; no Kubernetes/EKS | Confirmed baseline |
| A03 | ₹50,000 default; 0.5% per-trade risk; 1.5% daily breaker | Confirmed defaults; additional limits unresolved |
| A04 | Telegram session approval | Confirmed baseline; detailed policy unresolved |
| A05 | Live release is separate future scope | Confirmed |
| A06 | Create local Git repository for future source code and Terraform | Authorized 7 November 2026; scaffold created; no application/runtime or deployable resources implemented |
| A07 | Publish scaffold privately to GitHub; keep all local repositories inside current workspace | Authorized 8 November 2026; publication pending verification |

## 14. Change log

| Date | Change |
|---|---|
| 7 November 2026 | Created persistent master document from the planning specification and 51-task backlog. All delivery tasks remain Pending. |
| 7 November 2026 | Created local `groww-ai-trading-agent/` Git repository scaffold with source, tests, Compose, Terraform, documentation, and ignore rules. T14 remains Pending because runtime acceptance criteria and prerequisite gates are outstanding. No remote, AWS resources, or trades created. |
| 8 November 2026 | Moved the authoritative tracker into `docs/WORK-TRACKER.md` for portability, replaced the original external document with a link, and updated repository references. Private GitHub publication authorized; not yet verified. All 51 delivery tasks remain Pending. |

## 15. Next work session

Start T01: record the allowed instruments, initial stock universe, intraday/swing scope, and exclusions. Resolve material owner choices before marking Done. Then select the next eligible task. Continue planning until implementation is explicitly authorized.

When resuming in another chat, read this document first and carry forward its current task states and decisions. Updates occur while we work together; this document does not run background work or monitoring.
