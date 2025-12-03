Full EPIC List (EPIC 1 → EPIC 8)

With estimated time, % of project, and summary

This reflects the final, stable structure we agreed upon based on your actual system architecture and the implemented work.

Epic #	Name	                                                Description	Est. Time	% of Total
1	Database Schema & Core Models	                        Accounts, Portfolio, Instruments, Contracts, Orders, Executions, Positions, OptionEvents	~3 days	12%
2	Broker Connector Abstraction + FakeBroker Testing Infra	IBKR abstraction layer, dataclasses, FakeBrokerAPI, connector plumbing	~4 days	16%
3	Trade & Account Ingestion Layer	Snapshot ingestion, positions ingestion, orders, executions, option events, tests	~6 days	24%
4	Strategy Engine (v1)	StrategyInstance, strategy runner, signal models, opportunity scanner foundation, risk hooks	~7 days	28%
5	Execution & Order Placement Layer	Send orders, roll logic, safety rules, broker throttling, audit logs	~3 days	12%
6	Backtesting Engine (v1)	Replay historical broker data, run strategies offline, compare outputs	~4 days	16%
7	User Interface (Phase 1)	Minimal dashboard: overview, positions, orders, signals, logs	~3 days	12%
8	Monitoring, Logging, Observability	Admin pages, ingestion logs, job scheduler, alerts	~2 days	8%
🎯 Total Estimated Time for Phase 1 = ~32 days of focused work

(You are currently 34–36% done by complexity — because EPICs 1–3 are foundational and heavier than later ones.)

🚀 Future Extensions / Phase 4+ (Advanced Work)

These are not required for a complete Phase 1 system.
They represent the Evolution Path.

Phase 4 — Advanced Strategy Layer (Theta Farm, Wheel++ hybrids)

Multi-strategy allocation

Capital optimization

Multi-account synchronization

IBKR risk API integration

Parametric strategy configuration UI
Estimate: 10–14 days

Phase 5 — TFSA / Non-Margin Optimization

Marginless constraints

Low-risk CSP allocation

Covered-call ladder automation

TFSA-safe strategy guardrails

Tax-aware returns reporting
Estimate: 5–7 days

Phase 6 — Market Data Ingestion & Scanner v2

Live quotes

Volatility surfaces

IV rank computation

Option chain ingestion

Opportunity ranking engine
Estimate: 10–12 days

Phase 7 — Mobile App or UI Upgrade

Full interactive dashboard

Strategy edit/enablement

Notifications
Estimate: 8–12 days

Phase 8 — ML-Assisted Optimization (optional future)

Order sizing recommendation

Auto-roll heuristics

Regime detection model
Estimate: 14+ days

📌 Summary Table
Phase 1 (Epics 1–8)

32 days total

Covers everything needed for automated real-money trading for your portfolio.

Phase 4+ (Future expansions)

~50 additional days, fully optional.

Covers long-term evolution: TFSA-safe engine, market data scanners, ML enhancements.