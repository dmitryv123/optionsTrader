Database schema now supports:

## 1. Snapshots  
- Unique constraint: `(broker_account, asof_ts)`  
- Ordering: `get_latest_by = "asof_ts"`

✔️ Compatible with ingestion

---

## 2. Positions  
- Index on `(client, broker_account, asof_ts)`  
- Natural key handled externally (we overwrite each sync)

✔️ Compatible

---

## 3. Orders  
- Unique constraint `(broker_account, ibkr_order_id)`  

✔️ Exactly what IBKR lifecycle requires

---

## 4. Executions  
- Unique `ibkr_exec_id`  

✔️ Append-only by design

---

## 5. Option Events  
- Indexed by client, event_ts, event_type  

✔️ Compatible with ingestion

---



---