# Ingestion Pipeline — Architecture & Developer Guide

This document describes the ingestion pipeline implemented in EPIC 3.  
It covers:

- Broker abstraction layer  
- FakeBroker test support  
- Ingestion modules (`accounts_sync`, `positions_sync`, `orders_sync`, `executions_sync`, `option_events_sync`)  
- Dataclasses  
- Upsert semantics  
- Test architecture  
- Expected usage patterns  

---

# 1. Broker Abstraction Layer

The ingestion pipeline does **not** talk directly to IBKR.  
Instead, it calls a unified interface:

#```python
from trading.brokers.registry import get_broker_client
client = get_broker_client(broker_account)
The returned object must implement:

python
Copy code
class BrokerAPI:
    def fetch_account_snapshots(self): ...
    def fetch_positions(self): ...
    def fetch_open_orders(self): ...
    def fetch_executions(self): ...
    def fetch_option_events(self): ...
This abstraction gives us:

easy testing (FakeBrokerAPI)

ability to interchange IBKR / TWS / Gateway / paper accounts

clean separation between transport and business logic

2. Dataclasses (Normalized Transport Format)
All ingestion relies on strongly typed dataclasses:

python
Copy code
AccountSnapshotData
PositionData
OrderData
ExecutionData
OptionEventData
These classes normalize:

timestamps

numeric fields (Decimal)

broker codes (account_code)

contract identifiers (con_id, symbol)

They are the only data format ingestion functions accept.

3. FakeBrokerAPI (Testing Layer)
For tests, we use:

bash
Copy code
trading/brokers/testing.py
FakeBrokerAPI implements the same BrokerAPI interface:

python
Copy code
class FakeBrokerAPI(BrokerAPI):
    def __init__(snapshots, positions, orders, executions, option_events)
This enables deterministic unit tests for ingestion.

Example usage:

python
Copy code
fake = FakeBrokerAPI(
    snapshots=[AccountSnapshotData(...)]
)
mock_get_client.return_value = fake
4. Ingestion Modules

## 4.0 High-Level Data Flow

```mermaid
flowchart LR
    A[IBKR / Broker Transport] 
        --> B[BrokerAPI Adapter<br/>(IBKRClient / FakeBrokerAPI)]
    B --> C[Normalized Dataclasses<br/>(OrderData, ExecutionData,<br/>OptionEventData, etc.)]
    C --> D[Ingestion Functions<br/>(orders_sync, executions_sync,<br/>positions_sync, option_events_sync)]
    D --> E[Django ORM Models<br/>(Order, Execution, Position,<br/>OptionEvent, AccountSnapshot)]
This diagram makes it visually obvious that ingestion is:

Broker → Adapter → Dataclass → Ingestion → Models

Each ingestion module is a pure function:

bash
Copy code
trading/ingestion/accounts_sync.py
trading/ingestion/positions_sync.py
trading/ingestion/orders_sync.py
trading/ingestion/executions_sync.py
trading/ingestion/option_events_sync.py
4.1 Upsert Rules
Each module uses idempotent upsert semantics:

Account Snapshots
natural key: (broker_account, asof_ts)

newest snapshot is always inserted

Positions
natural key: (broker_account, instrument)

always updated on new sync

Orders
natural key: (broker_account, ibkr_order_id)

supports updates (Submitted → Filled → Cancelled)

Executions
natural key: ibkr_exec_id

executions are never updated, only inserted

Option Events
natural key: (broker_account, ibkr_con, event_ts, event_type)

events are append-only

5. Test Architecture
The trading/brokers/tests/ suite validates:

✔️ Snapshot ingestion
✔️ Position ingestion
✔️ Order ingestion
creation

updates (Submitted → Filled)

contract resolution

✔️ Execution ingestion
idempotent insert

✔️ Option event ingestion
append-only

duplicate detection

The FakeBrokerAPI is mutated between sync calls to simulate real market state.

6. Developer Usage Example
python
Copy code
from accounts.models import BrokerAccount
from trading.ingestion.orders_sync import sync_orders_for_broker_account

ba = BrokerAccount.objects.get(account_code="U1234567")
summary = sync_orders_for_broker_account(ba)
print(summary)  # {"created": 1, "updated": 2, "total": 3}

7. TODO (Phase 2 / Phase 4)
bulk ingestion optimizations
streaming ingestion
lock-free upsert patterns
drop-in replacements for other brokers
production observability hooks