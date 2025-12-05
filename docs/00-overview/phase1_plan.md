# Phase 1 — Core System Foundation  
_Last updated: 2025-11-26_

## 1. Phase Overview

Phase 1 establishes the **entire foundation** of your OptionsTrader system:
- All database schema and relationships
- IBKR ingestion pipelines
- Normalized market and account data
- Opportunity scanning framework (basic)
- Strategy and recommendation infrastructure
- Initial UI
- Observability & logging

❗ **No autonomous trading is done in Phase 1.**  
All recommendations are visible only in the UI.

---

## 2. Architecture Components in Phase 1

### 2.1 Backend (Django)

Core apps involved:
- `accounts`
- `portfolio`
- `strategies`
- `marketdata` (optional)
- `opportunities`
- `recommendations`

Phase 1 ensures:
- All models are correct, normalized, linked
- IBKR data flows into those models
- Recommendations flow through strategy harness

---

## 3. Phase 1 Deliverables

### 3.1 Database Models (Complete & Stable)

#### Accounts App
- Client  
- ClientMembership  
- BrokerAccount  
- AccountSnapshot  

#### Portfolio App
- Instrument  
- IbkrContract  
- Portfolio  
- Position  
- Order  
- Execution  
- OptionEvent  

#### Strategies App
- StrategyDefinition  
- StrategyVersion  
- StrategyInstance  
- StrategyRun  
- Signal  
- Opportunity  
- Recommendation  

---

## 4. IBKR Connector Service (Phase 1 Requirements)

### 4.1 Account Ingestion
- Net liquidation value  
- Maintenance margin  
- Buying power  
- Cash  
- Snapshot stored in `AccountSnapshot`

### 4.2 Positions Ingestion
- Build/refresh `Position` table  
- Sync IBKR contract → IbkrContract mapping  
- Maintain proper timestamps

### 4.3 Market Data Ingestion (Snapshot Mode)
- Pull quotes for:
  - underliers
  - options selected by scanners
- Store:
  - bid/ask
  - last
  - IV (if available)
  - Greeks (if available)
  - volume/open interest (if available)

### 4.4 Order/Execution Sync (Read-Only)
- Sync IBKR orders into `Order`
- Sync executions into `Execution`

---

## 5. Data Normalization Layer

Implement:
- Symbol → Instrument mapping
- con_id → IbkrContract hydration
- Expiry / Strike canonicalization
- Underlier → option chain resolver
- Eliminating IBKR noise/duplication

---

## 6. Opportunity Scanner (Basic Engine)

Purpose:
- Process underliers
- Apply filters (volume/price/IV/delta)
- Rank candidates  
- Store candidates in `Opportunity`

Phase 1 version supports:
- CSP candidates for Wheel  
- CC candidates  
- Theta candidates  
- Sorted by ROR, IV rank, liquidity

Full automation comes later (Phase 2).

---

## 7. Recommendation Engine (Foundational)

Implements:
- BaseRecommendationBuilder
- Produce “paper” recommendations (not placing trades)
- Types include:
  - `sell_put`
  - `sell_call`
  - `roll_put`
  - `roll_call`
  - `close`

Recommendations flow:
Opportunity → StrategyInstance → Recommendation table → UI.

---

## 8. User Interface (Phase 1 UI)

Pages included:
- Dashboard (account summaries)
- Positions
- Portfolios
- Strategy Instances (create/configure/toggle enabled)
- Opportunities list
- Recommendations list (Phase 1 "paper trading")

Minimalistic but functional.

---

## 9. Observability & Logging

Include:
- API request logs  
- Strategy debug logs  
- Opportunity scan logs  
- Daily snapshot logs  
- Error tracking  
- Audit trails (DB)

---

## 10. Phase 1 Success Criteria

Phase 1 is complete when:
- All ingestion pipelines run reliably
- Strategies can produce PAPER recommendations
- Recommendations show in UI
- Logs are complete
- Database schema is steady (no major changes)
- No automated trading happens, only visibility

---

## 11. Transition to Phase 2

Phase 2 focuses on:
- Automated trades
- Full PM-aware Risk Engine
- Assignment engine
- Order Manager
- Real execution

Phase 1 is the foundation for all of that.


