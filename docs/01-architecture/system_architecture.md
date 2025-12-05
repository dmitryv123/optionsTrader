# System Architecture

This document provides a high-level view of the OptionsTrader system.

## Components

- **Backend**: Django + PostgreSQL
- **Broker Connector**: IBKR client abstraction, FakeBroker for tests
- **Strategy Runtime**: StrategyEngine, StrategyContext, strategy plugins (e.g., WheelStrategy v1)
- **Data Layer**: Accounts, Portfolio, Positions, Orders, Executions, OptionEvents
- **Planned Frontend**: React/TypeScript UI for dashboards and execution plans

## Diagrams

See also:

- `system_architecture_sequence.mmd`
- `system_architecture_dataflow.mmd`
- `system_architecture_classes.mmd`

These can be rendered with any Mermaid-capable tool.
