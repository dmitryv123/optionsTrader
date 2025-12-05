flowchart LR

    subgraph BROKER_STATE[DB: Portfolio State]
        AS[AccountSnapshot]
        POS[Positions]
        EXE[Executions]
    end

    SI[StrategyInstance] --> CFG[Config Merge\n(User Config + Defaults)]
    CFG --> SC[StrategyContext]

    BROKER_STATE --> SC

    SC --> EVAL[WheelStrategy.evaluate()]
    EVAL --> SIG[Signals]
    EVAL --> OPP[Opportunities]
    EVAL --> REC[Recommendations]

    SIG --> DB_SIG[(strategies_signal)]
    OPP --> DB_OPP[(strategies_opportunity)]
    REC --> DB_REC[(strategies_recommendation)]

    SC --> RUN_START[(StrategyRun start)]
    RUN_START --> RUN_END[(StrategyRun complete)]
