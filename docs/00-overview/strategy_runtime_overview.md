Strategy Runtime Architecture — Overview (Epic 4, Story 4.7)

(Tasks: T0062.1–T0062.4)

T0062.1 — StrategyEngine Architecture & Data Flow
1. High-Level Runtime Pipeline
StrategyInstance
      │
      ▼
StrategyEngine.run_strategy()
      │
      │ 1) Load Context:
      │    - AccountSnapshot (latest)
      │    - Positions
      │    - Executions
      │    - Strategy config
      ▼
StrategyContext(dataclass)
      │
      ▼
Strategy implementation (e.g., WheelStrategy.evaluate())
      │
      │ Produces: 
      │   - signals[]
      │   - opportunities[]
      │   - recommendations[]
      ▼
Actions(dict of lists)
      │
      ▼
StrategyEngine persistence layer
      │
      ├── create StrategyRun
      ├── (optional) persist Signals
      ├── (optional) persist Opportunities
      └── (optional) persist Recommendations

2. Module-Level Responsibilities
StrategyEngine

Orchestrates the lifecycle of a strategy evaluation.

Loads all state required for a deterministic evaluation run.

Wraps execution in proper exception handling.

Persists a StrategyRun row (success or error).

Routes action outputs to persistence methods.

StrategyContext

A pure dataclass with:

client

portfolio

broker_account

snapshot (AccountSnapshot)

positions (list)

executions (list)

config (merged config for this strategy instance)

any convenience computed fields (equity, risk metrics, etc.)

Context is explicitly read-only — strategies cannot mutate models.

Strategy Implementation (WheelStrategy, etc.)

Receives a StrategyContext.

Applies configuration rules (delta target, DTE target, cash thresholds).

Outputs only domain objects (signals/opps/recs); never writes DB.

3. Persistence Layer

Persistence happens only inside StrategyEngine:

Object Type	Table	Notes
Run summary	StrategyRun	Always persisted, even on errors
Signals	Signal	Optional; enabled via flags
Opportunities	Opportunity	Optional
Recommendations	Recommendation	Optional; default behavior = persist

Every persistence call is idempotent:

same StrategyInstance

same asof_ts

same underlying record
→ re-running does not produce duplicates.

T0062.2 — Config Schema & StrategyInstance Lifecycle
1. StrategyVersion

Represents a versioned "contract" for a strategy:

JSON schema:

defines required fields

defines ranges

defines allowed enumerations

code_ref: dotted import path of implementation

Example for WheelStrategy v1:

{
  "type": "object",
  "required": ["put_days_out", "put_delta_target"],
  "properties": {
    "put_days_out": {"type": "integer", "minimum": 0, "maximum": 60},
    "put_delta_target": {"type": "number", "minimum": 0.05, "maximum": 0.50}
  }
}

2. StrategyInstance Lifecycle
Creation

User selects StrategyDefinition (e.g., “Wheel”)

User selects version (“v1”)

User configures initial settings

We save StrategyInstance with raw config JSON

Validation

list_strategies --validate-configs performs:

schema validation

warns if strategy version cannot load implementation

prints missing or invalid fields

Execution

run_strategies or API-triggered:

loads instance

merges config with defaults

calls StrategyEngine.run_strategy_instance()

Evolution

When migrating from v1 -> v2:

Admin command migrate_wheel_configs updates instance configs in place

StrategyVersion.schema ensures new rules are satisfied

T0062.3 — Signals, Opportunities, Recommendations Usage & Storage
Signals

Low-level observations emitted by strategy logic.

Examples:

"profit_capture_status": {"pct": 32.5}

"market_trend": "bearish"

Stored in:

strategies_signal


Used for:

diagnostics

analytics

UI charts

debugging strategy behavior

Opportunities

Represent potential trades identified by the strategy.

Examples:

“Sell-to-open AAPL 150p expiring in 10 days”

“Good IV rank opportunity”

Stored in:

strategies_opportunity


Attributes:

metrics

required margin

notes

associated Instrument & IbkrContract

Used for:

UI "Opportunity Scan" screen

Backtesting

Risk dashboards

Recommendations

These are actual actionable outputs:

Examples:

{"action": "sell_put", "params": {"strike":150, "expiry":"2024-06-21", "qty":1}}


Stored in:

strategies_recommendation


Downstream usage:

feeds trade execution API layer (Epic 6)

used to build the "Execution Plan" UI (Epic 7)

supports audit logs

Idempotency Rules

A recommendation is uniquely determined by:

strategy_instance

asof_ts

underlier

action + params

Re-running the same strategy never duplicates records.

If market data changes, re-running produces a new asof_ts, not a mutation.

T0062.4 — Example Narrative: A Full WheelStrategy Run
Scenario

Client has $100,000 cash

No positions

Config:

put_days_out = 7

put_delta_target = 0.20

1. StrategyEngine loads context

latest AccountSnapshot → cash = 100k

positions = []

executions = []

config merged

Context summary:

cash = 100000
universe = ["AAPL", "MSFT", ...]
put target = 7DTE, Δ=0.20

2. WheelStrategy.evaluate(context)
a) Step 1: Identify eligible underliers

Screening rules reject:

earnings this week

extreme volatility

underliers with insufficient liquidity

Suppose AAPL passes.

b) Step 2: Compute candidate put

Based on delta target:

choose strike ≈ Δ 0.20

choose expiry ≈ 7 days out
E.g. AAPL 150p expiring Friday.

c) Step 3: Risk checks

Available cash > required collateral

Margin impact acceptable

Portfolio has no conflicting open short puts

Checks pass.

d) Step 4: Emit actions

WheelStrategy outputs:

Signals

[
  {"type":"universe_screen", "payload":{"passed":["AAPL","MSFT"]}},
  {"type":"delta_calc", "payload":{"AAPL":{"target":0.2,"selected_strike":150}}}
]


Opportunities

[
  {"underlier":"AAPL”, "metrics":{"delta":0.21, "dte":7}}
]


Recommendations

[
  {"action":"sell_put", 
   "underlier":"AAPL",
   "params":{"strike":150,"expiry":"2024-06-21","qty":1}}
]

3. Persistence Layer Produces:

StrategyRun row

2 Signals

1 Opportunity

1 Recommendation

4. UI (Epic 7) Will Show:
Execution Plan

Sell Put: AAPL 150p exp 6/21 qty 1

Reason: IV rank favorable, Δ targeting met, cash sufficient

Diagnostics Panel

universe screen results

delta computations

cash and margin check summary

Opportunity Scan

list of all viable candidates