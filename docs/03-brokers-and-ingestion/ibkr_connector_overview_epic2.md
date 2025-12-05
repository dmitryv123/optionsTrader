EPIC 2 — Interactive Brokers Connector

Goal:
Build a clean, vendor-agnostic broker integration layer with IBKR as the first supported broker.
This epic provides ingestion for:

Account snapshots

Open positions

Mapping raw broker data into normalized internal types

Persisting snapshots into Django models

Running ingestion via management commands

Providing a testing framework (Fake Broker)

This epic completes the entire data ingestion pipeline required for Strategy Engine, Risk Engine, and Execution Engine in later phases.

1. Architecture Overview

EPIC 2 introduces the following components:

trading/
  brokers/
    base.py          # BrokerAPI Protocol
    types.py         # normalized dataclasses (AccountSnapshotData, PositionData)
    exceptions.py    # UnsupportedBrokerError, BrokerConnectionError, etc.
    registry.py      # get_broker_client()

    ibkr/
      config.py      # IBKRConnectionConfig, env/settings loader
      transport.py   # IBKRTransport (thin wrapper over real IBKR connectivity)
      mappers.py     # raw → normalized dataclass conversion
      client.py      # IBKRClient implementing BrokerAPI

  ingestion/
    accounts_sync.py  # persist AccountSnapshot
    positions_sync.py # persist Position, Instrument, IbkrContract


This structure ensures:

No external IBKR SDK leaks into the rest of the system

All broker-specific logic is contained under brokers/ibkr/

The ingestion pipeline remains stable even if the transport layer changes

Strategies, risk engine, execution engine, and UI do not depend on IBKR internals

2. Broker Abstraction Layer
2.1 BrokerAPI (Protocol)

Defines the interface all brokers must implement:

fetch_account_snapshots() -> Iterable[AccountSnapshotData]
fetch_positions() -> Iterable[PositionData]


No IBKR-specific behavior or raw payloads leak outside of the transport layer.

2.2 Normalized Data Types

Stored in:

trading/brokers/types.py

AccountSnapshotData

Normalized representation of:

cash

buying power

margin use

maintenance requirements

timestamp

broker extras

PositionData

Normalized representation of:

symbol, exchange

contract ID

quantity, avg cost

market price/value

timestamp

raw payload (for debugging)

These dataclasses allow ingestion to remain vendor-agnostic.

3. IBKR Connector Implementation
3.1 Configuration (ibkr/config.py)

IBKRConnectionConfig defines:

host

port

client_id

use_gateway

Values can come from:

Django settings (IBKR_HOST, IBKR_PORT, etc.)

Environment variables

Default fallbacks

3.2 Transport Layer (ibkr/transport.py)

A minimal wrapper around IBKR connectivity.

connect()

disconnect()

fetch_raw_account_data(account_code)

fetch_raw_positions(account_code)

For EPIC 2 this is stubbed; real implementation begins in EPIC 3.

3.3 Raw Data Mappers (ibkr/mappers.py)

Converts raw IBKR payloads into normalized internal types:

_to_decimal

_to_datetime

map_raw_account_to_snapshot(...)

map_raw_positions(...)

This isolates normalization and value sanitization into a clean, testable layer.

3.4 IBKR Client (ibkr/client.py)

Implements BrokerAPI using:

transport

mappers

configuration

Provides:

fetch_account_snapshots()

fetch_positions()

Ensures proper lifecycle with try/finally for connect/disconnect.

4. Ingestion Pipeline
4.1 Account Snapshot Ingestion

sync_account_snapshot_for_broker_account(broker_account)

resolves client using registry

fetches normalized snapshot

writes to AccountSnapshot model

preserves raw metadata

wrapped in atomic transaction

4.2 Positions Ingestion

sync_positions_for_broker_account(broker_account, portfolio=None)

Creates:

Instrument

IbkrContract

Position rows

Supports:

auto-selecting portfolio

atomic transaction wrapping

snapshot-only mode (never overwrites past positions)

5. Management Commands

For manual and scheduled ingestion:

./manage.py sync_ibkr_account_snapshots
./manage.py sync_ibkr_positions


Both commands:

filter automatically by LIVE/PAPER broker accounts

allow optional --account <code>

produce clean CLI summaries

6. Testing Support

EPIC 2 includes a testable fake broker:

trading/brokers/testing.py

FakeBrokerAPI

make_simple_fake_account_snapshot

make_simple_fake_position

Used in:

test_account_ingestion

test_positions_ingestion

These tests ensure ingestion works without IBKR Gateway/TWS.

7. Completion Criteria

EPIC 2 is fully complete when:

✔ All modules compile and run
✔ sync_ibkr_account_snapshots creates valid snapshot rows
✔ sync_ibkr_positions creates valid Position, Instrument, IbkrContract rows
✔ FakeBroker tests pass
✔ No IBKR SDK is imported outside of ibkr/transport.py
✔ Documentation file (this one) exists in docs/
8. Next Steps (EPIC 3 Preview)

EPIC 3 introduces trade/transaction ingestion:

Orders

Executions

Option assignments/exercises

Real IBKR transport implementation

Sync loop for order statuses

Storage of execution audit trails

Detailed breakdown will be generated next.