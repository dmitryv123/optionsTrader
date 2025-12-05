StrategyInstance → StrategyEngine → StrategyRuntime → WheelStrategy → Persistence Layer

sequenceDiagram
    autonumber

    participant UI as Caller / Scheduler
    participant SE as StrategyEngine
    participant SR as StrategyRuntime
    participant WS as WheelStrategy
    participant DB as Django ORM / DB

    UI->>SE: run_strategy_instance(strategy_instance, asof_ts)
    SE->>DB: Load StrategyInstance + StrategyVersion
    SE->>DB: Load latest AccountSnapshot
    SE->>DB: Load Positions
    SE->>DB: Load Executions
    SE->>SE: Build StrategyContext

    SE->>SR: evaluate_strategy(context)
    SR->>WS: evaluate(context)
    WS-->>SR: actions = {signals, opportunities, recommendations}

    SR-->>SE: actions

    SE->>DB: Create StrategyRun(started)
    alt persist_signals enabled
        SE->>DB: Insert Signal rows
    end
    alt persist_opportunities enabled
        SE->>DB: Insert Opportunity rows
    end
    alt persist_recommendations enabled
        SE->>DB: Insert Recommendation rows
    end

    SE->>DB: Update StrategyRun(completed)
    SE-->>UI: return actions (in-memory plan)
