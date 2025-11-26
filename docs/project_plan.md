# 1. Overview
This document describes the complete engineering plan for theOptionsTrader automated trading system integrating:
IBKR live trading
Multi-account, multi-portfolio support
PM-aware risk management
Strategy engine (Wheel, Theta, Covered Calls, etc.)
TFSA-safe strategy support
Recommendation + Order pipelines
Backtesting + analytics
Full automation architecture

The roadmap is structured across four major phases:
Phase 1: Core architecture, ingestion, models, storage, observability
Phase 2: Strategy Engine + Auto-Trading Engine
Phase 2.5: TFSA Module (Covered Calls, LEAPS strategies)
Phase 3: Full AI automation + scaling
Phase 4: Advanced/optional expansion

# 2. Architecture (High-Level)
Components:
IBKR Connector Service (market data + account data + order management)
Django Backend (core APIs, persistence, risk logic)
Strategy Engine (Wheel, Theta, CC overlay, LEAPS engine)
Risk Engine (PM rules + TFSA rules)
Recommendation Engine
Order Manager (turn recommendations → executable orders)
Scheduler (daily runs, multi-DTE logic)
PostgreSQL Database
React Typescript UI
Backtesting subsystem
Logging/Monitoring services

# 3. Phase 1 — Core System Foundation
Phase Goal: A stable system that ingests IBKR data, stores it, displays positions, and can produce strategy recommendations — but does NOT place trades automatically yet.

3.1 Models & Persistence
Already implemented or partially done — finalize:
Accounts App
Client
ClientMembership
BrokerAccount
AccountSnapshot
Portfolio App
Instrument
IbkrContract
Portfolio
Position
Order
Execution
OptionEvent
Strategies App
StrategyDefinition
StrategyVersion
StrategyInstance
StrategyRun
Signal
Opportunity
Recommendation

3.2 IBKR Connector Service
Implement:
Account Summary ingestion
Portfolio Positions ingestion
Market Data ingestion (snapshot)
Order/Execution streaming
Rate-limited updates (2–5s)
Reconnect + retry logic
Backfill capabilities
Outputs → DB tables AccountSnapshot, Position, Order, Execution, Instrument, IbkrContract

3.3 Data Normalization Layer
Functions:
Merge repeated IBKR updates
Clean symbol/contract mapping
Create underlier → options mapping table
Normalize Greeks
Normalize expirations/strikes

3.4 Opportunity Scanner Framework (Foundational Only)
Create Reusable Scanner Base:
Fetch underliers
Apply filters (IV, Delta, DTE, liquidity)
Rank by ROR%, PM usage, Theta, etc.
Store to Opportunity table
(Deep logic comes in Phase 2.)

3.5 Recommendation Engine (Foundational)
A generic structure that:
Takes Opportunities
Applies strategy rules
Produces Recommendations
Stores recommendations to DB
No order placement yet.

3.6 User Interface (Phase 1 UI)
Implement:
Dashboard: balances, positions, key metrics
Strategy Instances UI: config editor
Opportunities browser
Recommendations viewer
Portfolio view

3.7 Observability
Add:
Logging service
Daily snapshot logging
Error tracker
Audit trail for recommendations and signals

Phase 1 Deliverables
DB schema stable
IBKR ingestion stable
Strategy framework in place
Recommendations appear in UI
No trades executed automatically

# 4. Phase 2 — Strategy Execution & Auto-Trading
Phase Goal: Strategies generate actions AND the system executes them automatically with proper risk controls.

4.1 Strategy Engine (Full Implementation)
Implement these strategies:
S1. Wheel / Cash-Secured Put
Entry filter
Delta & DTE rules
PM-aware sizing
Assignment handling
Auto-roll logic
S2. Covered Calls (for main PM accounts)
CC on long stock
Delta target
Roll ITM / roll early / manage earnings exposure
S3. Theta Farming (Short premium on indexes)
Weekly SPY/QQQ short puts
Delta < 0.20
Auto-roll logic
PM-aware size controls
S4. Assignment Engine
Capture assignments
Adjust positions
Trigger CC → next step

4.2 Risk Engine (Full PM Mode)
Logic:
Maintenance margin consumption
Buying power rule
Max portfolio PM utilization
Portfolio-level VaR
Max position size per ticker
Weekly PM usage reporting

4.3 Order Manager
Convert recommendation → executable IBKR order
Validate risk
Smart routing
Multi-leg orders (if needed)
Roll logic
Partial fills
OCA groups
GTC support

4.4 Scheduling Engine
Daily tasks (scan → recommend → trade)
Expiry tasks (rolls, close management)
5-minute incremental monitors for risk

4.5 UI Enhancements
Trade journal
Strategy dashboards
Auto-trading toggle per strategy instance

Phase 2 Deliverables
Fully automated trading
PM risk controls
Complete Wheel/Theta automation
Assignment automation
Reliable execution pipeline

# 5. Phase 2.5 — TFSA Strategy Module (NEW)
Phase Goal: Add TFSA-legal strategies using long-only positions and CC overlays, fully integrated with StrategyEngine & RecommendationEngine.

T1. TFSA Covered Call Overlay Strategy
StrategyDefinition: covered_call_overlay
Supported on:
long stock
long ETF
Inputs:
target delta
DTE
roll triggers
allowed tickers
Output: sell_call recommendations only
No naked options allowed

T2. LEAPS Synthetic Stock Module
StrategyDefinition: synthetic_stock_leaps
Buy deep ITM LEAPS
Sell monthly CC against them
TFSA-safe leveraging
Requires LEAPS liquidity / OI checks
Add delta-equivalent exposure checking to RiskEngine

T3. TFSA Risk Engine
Implement a parallel set of rules:
No margin
No naked options
No credit spreads
Max % allocation per ticker
Synthetic delta limits
Position concentration limits
TFSA-specific drawdown throttling

T4. TFSA Dashboard UI
Display:
long positions
CC expiries
roll dates
income stream
TFSA annual return
CC yield

T5. TFSA Backtesting Module
Historical covered-call profitability
LEAPS + CC backtesting
Delta selection optimization
Annualized return curves

Phase 2.5 Deliverables
Fully automated TFSA system
Covered calls on stocks/ETFs
LEAPS + CC available
TFSA-safe risk engine
Integrated with main UI

# 6. Phase 3 — Full AI Automation & Scaling
Phase Goal: Use AI to tune strategies, detect regime changes, and optimize allocation.

3.1 AI Allocation Engine
Suggest ticker allocations
Adjust based on volatility regime
Portfolio aggregation across accounts
3.2 AI Regime Detection
Identify:
high-vol regimes
trend/momentum
mean reversion windows
earnings season risk
macro events
3.3 Reinforcement/Adaptive Strategy Tuning
Auto-adjust DTE
Auto-adjust delta
Dynamic roll rules
AI-informed opportunities ranking
3.4 Multi-Strategy Portfolio Optimizer
Balance:
Wheel
Theta
CC
LEAPS
TFSA CC
Constrain risk across accounts

# 7. Phase 4 — Optional Advanced Modules
These are optional future enhancements:
Vol Surface Builder
Earnings Plays Engine
Spread Engine
Tail Hedge Module
Live Order-Book/Flow Integration
Synthetics Arbitrage
Futures integration

# 8. Final Deliverables Summary
A. Phase 1 — Core ingestion + strategy framework B. Phase 2 — Full auto-trading + PM risk C. Phase 2.5 — TFSA strategy suite D. Phase 3 — AI-driven optimization E. Phase 4 — Optional quant modules