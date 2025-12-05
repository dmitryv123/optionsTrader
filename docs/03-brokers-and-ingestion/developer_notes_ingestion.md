---

## **📄 developer_notes_ingestion.md**

#```markdown
# Developer Notes — Ingestion Subsystem

This document captures design decisions, edge cases, and things to know  
before extending or modifying the ingestion pipeline.

---

# 1. Design Philosophy

The ingestion layer must always be:

- deterministic  
- idempotent  
- side-effect-free  
- stable against malformed broker data  

The ingestion layer does *not* perform:

- risk validation  
- strategy decisions  
- position sizing  
- order placement  

It only moves data from **BrokerAPI → Django ORM**.

---

# 2. Common Edge Cases

## 2.1 Missing or stale contract metadata
Sometimes orders refer to con_ids we have not ingested yet.

We handle this with:

#```python
ibkr_con = IbkrContract.objects.filter(con_id=od.con_id).first()
A None contract is allowed.

2.2 Timestamps
The tests enforce timezone-aware timestamps.
Always use:

python
Copy code
from django.utils import timezone
timezone.now()
Never use:

python
Copy code
datetime.utcnow()
datetime.now()
2.3 BrokerAccount mismatches
Some brokers may report orders from multiple subaccounts.
We guard against this:

python
Copy code
if od.broker_account_code and od.broker_account_code != broker_account.account_code:
    continue
3. Future Improvements
Switch to bulk_create for faster ingestion

Add ingestion audit logs

Add checksum validation for order lifecycle

Add ingestion metrics to Prometheus

4. Coding Conventions
Always isolate ingestion in its own module

Use dataclasses as the single truth of record

Use atomic transactions for each broker account sync

Use update_or_create only for objects with stable natural keys