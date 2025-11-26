# Phase 1 – Full Professional Project Plan  
Automated Options Trading System  
**Scope: Backend + Slim UI (React/TypeScript)**  
**Goal:** Human-in-the-loop automated options framework with IBKR integration

---

# 0. Overview

Phase 1 delivers a **production-ready decision-support system** that:

- Connects to IBKR (live or paper)
- Ingests accounts, positions, contracts, and market data
- Builds portfolio & risk states
- Runs multiple strategies (Wheel, Theta)
- Produces Opportunities & Recommendations
- Allows human approval through a React/TS UI
- Converts Recommendations → Orders (simulated or IBKR live)
- Stores everything in Postgres  
- Provides logs, alerts, and basic diagnostics

**No fully automatic trading yet.**  
**Human approval required.**

---

# 1. Architecture Summary

### Backend
- **Django**
- **Postgres**
- **Python Strategy Engine**
- **Python Risk Engine**
- **IBKR Gateway/TWS client wrapper**
- Existing models in:
  - `accounts`
  - `portfolio`
  - `strategies`

### Frontend
- **React + TypeScript**
- Phase 1 UI: Slim (Dashboard, Strategies, Opportunities, Recommendations, Orders, Logs)

### Architecture Principles
- API-first  
- Separation of concerns  
- Strategy plugin system  
- Risk & domain models separate from ORM models  
- All actions logged  
- Safety > automation

---

# 2. Phase 1 Milestones

Phase 1 is split into **8 major milestones**, in dependency order.

---

## M1. Foundation & Housekeeping

### Objectives
Unify shared logic, fix early model issues, and solidify base conventions.

### Tasks
- Move `TimeUUIDModel` to `common.models`
- Review and clean models across apps
  - Fix `BrokerAccount.__str__`
  - Remove invalid FK defaults in `Recommendation`
- Run all migrations cleanly
- Register key models in Django admin

### Definition of Done
- Shared TimeUUIDModel
- Models validated & migrated cleanly
- Admin shows all key entities

---

## M2. IBKR Integration & Data Ingestion

### Objectives
Create a clean, minimal IBKR wrapper and ingestion workflow.

### Tasks
1. **IBKR Client Wrapper (`IbkrClient`)**
   - Connect, fetch positions, account summary, contract details
   - Reconnection handling

2. **Data Ingestion Tasks**
   - `sync_ibkr_positions`
   - `sync_ibkr_account_snapshot`
   - Normalize & create/update:
     - `Instrument`
     - `IbkrContract`
     - `Position`
     - `AccountSnapshot`

3. **Mapping Logic**
   - Safe and idempotent symbol → instrument matching
   - Correct `IbkrContract` creation

### Definition of Done
- Running ingestion commands populates:
  - Instruments
  - Contracts
  - Positions
  - AccountSnapshots

---

## M3. Portfolio & Risk Engine (Read-Only)

### Objectives
Create domain objects + risk logic independent of Django models.

### Tasks
1. **Domain Objects**
   - `AccountState`
   - `PositionState`
   - `RiskState`

2. **Risk Engine**
   - Build functions:
     - `build_account_state(broker_account_id)`
     - `compute_risk_state(account_state)`
   - Detect:
     - PM usage %
     - Concentration risk
     - Illiquidity risk (Phase 2)

### Definition of Done
- You can request a complete `AccountState` + `RiskState` for any BrokerAccount
- Basic alerts work

---

## M4. Strategy Engine v1

### Objectives
Enable strategy execution using domain objects, configs, and models.

### Tasks
1. **Strategy Plugin Interface**
   ```python
   class BaseStrategy:
       slug: str
       def generate_signals(self, account_state, risk_state, instance): ...
Strategy Loader

StrategyVersion.code_ref → Python class resolver

Two Strategies Implemented

Wheel

Theta (index short puts)
Initially: produce Signals + Opportunities, not orders

StrategyRun Orchestrator

Loop over enabled StrategyInstances

Produce:

StrategyRun

Signal rows

Opportunity rows

Definition of Done

Command run_strategies produces runs, signals, opportunities

M5. Recommendations → Order Flow (HITL)
Objectives

Convert Opportunities → Recommendations → Orders with human approval.

Tasks

Recommendation Builder

Convert strategy logic → Recommendation model rows

Attach:

StrategyInstance

StrategyVersion

Portfolio

BrokerAccount

REST API Endpoints

GET /api/recommendations/

POST /api/recommendations/{id}/approve/

POST /api/recommendations/{id}/reject/

Order Manager

Convert Recommendation → draft order payload

Simulated orders (Phase 1)

Optional IBKR live send

Store Order rows

Sync IBKR status periodically

Execution Listener

Parse IBKR execution reports → Execution rows

Definition of Done

Approving a recommendation creates Order rows

(Optional) Orders appear in IBKR paper account

Executions recorded

M6. Slim UI (React/TS)
Objectives

Useful, minimal, clean UI covering all Phase 1 interaction.
Designed to upgrade to Full UI later with minimal backend changes.

Screens

Login & Client Selector

Dashboard

Cash, equity, BP

PM usage

Positions count

Active strategies

Strategy Instances

List, enable/disable, edit config

Recent StrategyRuns

Opportunities

Table of metrics (ROR, delta, DTE, etc.)

Recommendations (HITL Core Screen)

List pending recommendations

“Approve” / “Reject”

Shows rationale, confidence, params

Orders & Executions

Filter by status

Link executions

Logs & Alerts

Show RiskEngine alerts

Strategy errors

Definition of Done

Fully usable from UI without Django admin

Approving from UI → creates Order rows → visible in UI

M7. Backtesting Skeleton
Objectives

Framework for later backtesting, using same strategy logic.

Tasks

Data source abstraction for historical data

Backtest runner

StrategyRun(mode=BACKTEST) rows

Summary stats in stats JSON

Definition of Done

Command:

manage.py backtest_strategy --strategy wheel --config config.json --data history.csv


produces runs + stats.

M8. Logging, Monitoring, and Final DoD
Objectives

Make Phase 1 production-grade.

Tasks

Structured logging (JSON-friendly)

Error capture in StrategyRun.errors

System health endpoints

Global kill switch:

autotrade_enabled = false (Phase 1 default)

API rate and safety limits

Phase 1 Acceptance Criteria

IBKR ingestion stable

Risk Engine producing alerts

Strategy Engine functional with Wheel + Theta

Recommendations produced & viewable

Approval → Order flow works end-to-end

Executions stored

UI fully usable for daily operation

No auto-trading; human-in-the-loop required

3. UI Upgrade Path (Phase 2 → Phase 3)

Because Phase 1 uses:

API-first design

Strategy plugins

Domain objects (not ORM models)

Separate Order Manager

Recommendation-driven workflow

Moving from Slim UI (Phase 1) → Full UI (Phase 2/3) requires:

Zero backend rewrite

Mostly adding additional screens:

Greeks visualizer

Full option chain viewer

Charts

Backtest visualizations

Multi-step plan editor

Backend foundation remains stable.

4. Suggested Repository Structure
backend/
  accounts/
  portfolio/
  strategies/
  common/
  engines/
    risk_engine/
    strategy_engine/
    order_manager/
    ibkr/
  api/
  scripts/
  tests/
frontend/
  src/
    components/
    pages/
    hooks/
    services/
docs/
  phase1_plan.md   ← THIS FILE
  architecture_diagram.pdf
  architecture_flowchart.pdf
  architecture_uml.pdf

5. Next Steps

Implement M1 Foundation

Build IbkrClient and ingestion jobs (M2)

Implement Risk Engine domain layer (M3)

Build StrategyEngine v1 (M4)

Implement Recommendation → Order Flow (M5)

Build Slim UI screens and connect them (M6)

At that point Phase 1 is complete.
