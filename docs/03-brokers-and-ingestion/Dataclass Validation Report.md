---

## ✔️ AccountSnapshotData

**Correct:**  
- broker_account_code  
- currency  
- asof_ts  
- cash  
- buying_power  
- maintenance_margin  
- used_margin  
- extras (dict)

---

## ✔️ PositionData

Fields required for Position model:

| PositionData Field | Position Model Field | Status |
|-------------------|----------------------|--------|
| instrument_symbol | → instrument FK       | ✔️ resolved via Instrument |
| con_id            | → IbkrContract FK     | ✔️ optional resolution |
| qty               | → qty                 | ✔️ |
| avg_cost          | → avg_cost            | ✔️ |
| market_price      | → market_price        | ✔️ |
| market_value      | → market_value        | ✔️ |
| timestamp         | → asof_ts             | ✔️ |

Everything aligns.

---

## ✔️ OrderData

Matches Order model completely:

- ibkr_order_id  
- parent_id  
- side  
- order_type  
- limit_price  
- aux_price  
- tif  
- status  
- created_ts  
- updated_ts  

All ingestion fields map correctly.

---

## ✔️ ExecutionData

Correct mappings:

- ibkr_exec_id → unique key  
- order_id / con_id → optional FK resolution  
- qty, price, fee → numeric fields  
- fill_ts → timestamp  

Everything matches.

---

## ✔️ OptionEventData

Aligns with:

- event_type  
- event_ts  
- qty  
- con_id  

Everything is correct.

---

# 📌 Overall Result

**All ingestion dataclasses match the models and ingestion processes perfectly.  
No changes required.**

---