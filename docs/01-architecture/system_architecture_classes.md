classDiagram

class StrategyInstance {
    UUID id
    Client client
    StrategyVersion strategy_version
    Portfolio portfolio
    JSON config
    bool enabled
}

class StrategyVersion {
    UUID id
    StrategyDefinition strategy_def
    string version
    JSON schema
    string code_ref
}

class StrategyContext {
    Client client
    Portfolio portfolio
    BrokerAccount broker_account
    AccountSnapshot snapshot
    list~Position~ positions
    list~Execution~ executions
    dict config
}

class StrategyEngine {
    +run_strategy_instance(instance, asof_ts)
    -load_context(instance, asof_ts)
    -persist_actions(...)
}

class WheelStrategy {
    +evaluate(context) dict
}

class Signal {
    UUID id
    Client client
    StrategyInstance strategy_instance
    datetime asof_ts
    Instrument underlier
    IbkrContract ibkr_con
    string type
    JSON payload
}

class Opportunity {
    UUID id
    Client client
    Instrument underlier
    IbkrContract ibkr_con
    JSON metrics
    Decimal required_margin
}

class Recommendation {
    UUID id
    Client client
    Portfolio portfolio
    BrokerAccount broker_account
    StrategyInstance strategy_instance
    StrategyVersion strategy_version
    datetime asof_ts
    Instrument underlier
    IbkrContract ibkr_con
    string action
    JSON params
    Decimal confidence
}

StrategyInstance --> StrategyVersion : uses
StrategyEngine --> StrategyContext : creates
StrategyEngine --> StrategyInstance : loads
StrategyEngine --> WheelStrategy : invokes
WheelStrategy --> Signal : produces
WheelStrategy --> Opportunity : produces
WheelStrategy --> Recommendation : produces
