docs/epic3_trade_ingestion.md

EPIC 3 — Trade, Executions & Option Events Ingestion
1. Overview

EPIC 3 introduces ingestion of all transactional trading data from IBKR:

Orders

Executions (Fills)

Option Events (assignments, exercises, expirations)

It extends the broker abstraction built in EPIC 2 and provides full persistence into the existing Django ORM models:

Order

Execution

OptionEvent

This epic completes the read-only “Trade History” layer required before implementing the Strategy Engine, Risk Engine, and Execution Engine (in EPIC 4+).

2. Architecture Summary

New components introduced in EPIC 3:

trading/
  brokers/
    base.py            # BrokerAPI updated with trade methods
    types.py           # + OrderData, ExecutionData, OptionEventData
    exceptions.py      # + trade-related error classes

    ibkr/
      transport.py     # + raw order/execution/event fetchers
      mappers.py       # + mapping for order/execution/option_event
      client.py        # + BrokerAPI implementations

  ingestion/
    orders_sync.py
    executions_sync.py
    option_events_sync.py


This maintains complete isolation between:

broker-specific payload formats

normalized internal data models

ingestion logic

ORM persistence

3. Broker Abstraction Extensions
3.1 New normalized dataclasses

Added to trading/brokers/types.py:

OrderData

ExecutionData

OptionEventData

All dataclasses contain only normalized, broker-agnostic fields.

3.2 BrokerAPI Extensions

BrokerAPI now includes:

fetch_open_orders()

fetch_executions()

fetch_option_events()

Each returns an iterable of normalized dataclass instances.

4. IBKR Implementation
4.1 Transport Layer

New stub methods in ibkr/transport.py:

fetch_raw_open_orders(...)

fetch_raw_executions(...)

fetch_raw_option_events(...)

These are mapped to real IBKR endpoints later (EPIC 5).

4.2 Raw Mappers

ibkr/mappers.py converts raw IBKR data into:

OrderData

ExecutionData

OptionEventData

All numeric and datetime conversions reused from EPIC 2.

4.3 IBKR Client

ibkr/client.py implements:

fetch_open_orders()

fetch_executions()

fetch_option_events()

Internally:

transport → mapper → normalized dataclasses

Connection lifecycle through connect() / disconnect() remains unchanged.

5. Ingestion Layer

Three new ingestion modules:

orders_sync.py
executions_sync.py
option_events_sync.py


Each:

resolves the correct broker client

imports normalized dataclasses

persists data into Django models

ensures idempotency

runs inside atomic transactions

5.1 Orders

Upsert behavior for order status updates

Deduplication via (broker_account, ibkr_order_id)

5.2 Executions

Linked to matching Order by ibkr_order_id

Deduplication by ibkr_exec_id

Raw payload saved for audit

5.3 Option Events

Assignment, exercise, expiration

Linked to IbkrContract and Instrument

Deduplication by (broker_account, con_id, event_ts, event_type)

6. Management Commands

New commands under:

portfolio/management/commands/

sync_ibkr_orders

sync_ibkr_executions

sync_ibkr_option_events

Each supports:

--account <code> filtering

Live + Paper accounts only

Clean CLI summaries

7. Testing

EPIC 3 extends the fake broker system introduced earlier.

7.1 FakeBrokerAPI adds:

orders

executions

option_events

7.2 Helpers

make_simple_fake_order

make_simple_fake_execution

make_simple_fake_option_event

7.3 Unit tests

order ingestion tests

execution ingestion tests

option event ingestion tests

management command invocation tests

All ingestion behavior is testable without IBKR Gateway.

8. Completion Criteria

EPIC 3 is complete when:

✔ BrokerAPI supports trades
✔ IBKR client implements the new methods
✔ Orders, Executions, Option Events ingest correctly
✔ Tests cover ingestion & management commands
✔ Documentation file (this one) exists
9. Next Steps — EPIC 4 Preview

EPIC 4 introduces:

Strategy Engine input model

StrategyInstance runtime pipeline

Event-driven triggers from trades

Execution planner (dry run logic only)

Risk overlays before order submission

It is the first epic where the system begins to think.

End of epic3_trade_ingestion.md