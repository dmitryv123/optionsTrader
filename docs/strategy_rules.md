# Strategy Rules — Master Reference  
_Last updated: 2025-11-26_

This document defines the master set of rules for all strategies supported or planned within the OptionsTrader system.

It applies to:
- Phase 1 (recommendation-only)
- Phase 2 (auto-trading)
- Phase 2.5 (TFSA strategy suite)
- Phase 3 (AI adaptive variants)

---

# 1. Wheel Strategy (Cash-Secured Put → Covered Call)

## Purpose
Generate income while accumulating high-quality stocks at discounted prices.

## Entry Conditions
- Underlier price > $20  
- IV Rank ≥ 20  
- Spread width < 3% of price  
- Delta target: 0.15–0.30  
- DTE: 25–45  
- Liquidity: OI > 200, volume > 50  
- PM utilization after entry below configured threshold  

## Core Logic
1. Sell cash-secured put in target delta/dte range  
2. Take assignment if expires ITM  
3. Once long shares: begin Covered Call cycle  
4. Manage rolls early if:  
   - delta > 0.35 ITM  
   - profit > 60% early  
   - earnings protection required  
5. Repeat cycle  

## Exit Rules
- Close position when CC expires OTM  
- Or roll CC N days before expiry  
- Or stop-loss if underlying breaks defined levels  

---

# 2. Theta Strategy (Short Premium on Broad Indexes)

## Purpose
Weekly or bi-weekly Theta harvesting on SPY/QQQ/IWM under PM.

## Entry Conditions
- Underlier indexes only (SPY/QQQ/IWM/XSP)  
- IV Rank ≥ 15  
- Delta target: 0.10–0.20  
- DTE: 7–15  
- Liquidity must be excellent  
- PM usage below limits  

## Core Logic
- Short put or short put spread  
- Roll early at 50–70% profit  
- Avoid holding through CPI/FOMC (configurable)

## Risk Rules
- Max % PM allocated: configurable (e.g., 40–50%)  
- No earnings risk  
- Spread width validated  

---

# 3. Covered Call Strategy (PM Account)

## Purpose
Generate income on existing long stock.

## Entry Conditions
- Must have long stock shares  
- Select strike with delta 0.15–0.35  
- DTE: 20–45  
- OI > 200, volume > 20  

## Core Logic
- Sell CC monthly/bi-monthly  
- Roll up/out based on:  
  - delta > 0.35  
  - profit target achieved  
  - assignment risk  
  - earnings avoidance  

---

# 4. LEAPS + Covered Calls (PM or TFSA)

## Purpose
Synthetic stock with lower capital usage (PM) or TFSA-legal leverage.

## Entry Conditions
- LEAPS DTE: 365–720  
- Delta 0.70–0.90  
- Deep ITM  
- Sufficient OI  
- Spread < $0.80  

## CC Overlay
Identical to covered call rules above.

## Exit / Roll
- Roll LEAPS 90–120 days before expiry  
- If delta drops below threshold, refresh position  

---

# 5. TFSA Covered Call Strategy

See full details in `tfsa_strategy_rules.md`

Highlights:
- Long stock or ETF only  
- No naked exposure  
- Delta target 0.15–0.35  
- DTE 20–45  
- Optional roll logic  
- Conservative risk sizing  
- Focus on steady TFSA income  

---

# 6. TFSA LEAPS Synthetic Stock Strategy

Highlights:
- Buy LEAPS 70–90 delta  
- Use LEAPS as synthetic underlying for CC  
- Never sell more calls than LEAPS exposure  
- No naked selling  
- Roll LEAPS near 1y expiry window  

---

# 7. Assignment Engine Rules

Applicable to both Wheel and Covered Calls.

## Put Assignment
- Convert short put → long stock  
- Re-evaluate position cost basis  
- Begin CC cycle  
- Update portfolio and risk metrics  

## Call Assignment
- Convert short call → reduce/remove shares  
- Reset cost basis  
- Prepare new entry  

---

# 8. Roll Rules (Universal)

Roll triggers:
- delta exceeds configured threshold  
- profit exceeds threshold  
- approaching expiry (<7 days)  
- liquidity dry-up  
- earnings protection  
- PM adjustment needed  

Roll direction:
- Up and Out (O&O)  
- Out (O)  
- Up (U) rarely recommended  

---

# 9. Risk Engine — PM Accounts

Risk rules enforced before every trade:
- Max PM utilization  
- Buying power requirements  
- Max allocation per ticker  
- Max drawdown per strategy instance  
- IV / liquidity filters  
- Concentration limits  
- Conflict avoidance (overlapping risk)  

---

# 10. Risk Engine — TFSA Accounts

Full rules in TFSA doc. Key rules:
- No naked selling  
- No margin  
- Max allocation per ticker  
- Synthetic delta limits  
- Covered calls only  
- Long LEAPS allowed  
- Drawdown throttling  

---

# 11. StrategyInstance Configuration (JSON Schema Overview)

Each strategy instance includes:
- target_delta  
- dte_range  
- max_allocation  
- roll_rules  
- earnings_rules  
- liquidity_thresholds  
- PM or TFSA mode flag  
- universal risk flags  

---

# 12. Strategy Lifecycle

1. Input data ingestion  
2. Opportunity scanning  
3. Strategy evaluation  
4. Recommendation creation  
5. Risk validation  
6. Order execution (Phase 2/2.5)  
7. Logging + audit  
8. Roll/expiry management  

---

End of Document.
