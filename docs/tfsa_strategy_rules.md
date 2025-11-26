# TFSA Strategy Rules  
_Last updated: 2025-11-26_

This document defines all trading rules, constraints, and system logic required for **TFSA-safe trading strategies** within the OptionsTrader framework.

TFSA accounts require a **completely different risk model** than PM margin accounts.  
This document ensures full legal compliance and safe execution.

---

# 1. TFSA Trading Constraints

TFSA accounts **do not allow**:
- Margin
- Short selling
- Naked options (short puts or short calls)
- Credit spreads
- Multi-leg strategies requiring margin
- Synthetic shorts or leveraged exposures
- Pattern day trading (intraday options scalping)

The system must enforce all of the above **programmatically** in the TFSA Risk Engine.

Allowed strategies:
- Stock buying and selling  
- ETF buying and selling  
- Long calls & long puts  
- LEAPS (long only)  
- Covered calls on long stock  
- Covered calls on long LEAPS (synthetic stock)  
- Cash management ETFs  

---

# 2. TFSA Strategy Definitions

## 2.1 StrategyDefinition: `covered_call_overlay`

### Purpose
Generate consistent, low-risk income by selling calls against long stock/ETF positions.

### Inputs
- target_delta (0.15–0.35)
- dte (20–45 days)
- min_premium_yield
- roll_when:
  - delta_above
  - profit_pct
  - days_remaining
  - earnings_protection flag
- max_allocation_per_symbol
- blacklist_symbols

### Rules
1. Only allowed when sufficient long stock/ETF exists.
2. Must not sell more calls than shares owned.
3. Never sell naked calls.
4. Avoid low-liquidity options.
5. Use strike selection biased toward OTM, delta-based.

### Output Recommendation Types
- `sell_call`
- `roll_call`
- `close_call`

---

## 2.2 StrategyDefinition: `synthetic_stock_leaps`

### Purpose
Use deep ITM LEAPS (>365 DTE) as a stock surrogate, enabling covered calls without margin.

### Inputs
- leaps_min_dte (365)
- leaps_max_dte (730)
- leaps_delta_range (0.70–0.90)
- leaps_liquidity_threshold
- max_allocation_percent
- cc_target_delta
- cc_dte

### Rules
1. Buy on clean technical and liquidity filters.
2. Treat long LEAPS delta as “synthetic shares” in risk controls.
3. Covered calls must never exceed LEAPS-equivalent shares.
4. Roll LEAPS 90–120 days before expiry.

### Output Recommendation Types
- `buy_leaps`
- `sell_call`
- `roll_leaps`
- `roll_call`

---

# 3. TFSA Risk Engine Rules

The TFSA Risk Engine enforces:
- No margin usage (0% allowed)
- No short option exposure unless fully covered
- No credit or debit spreads requiring margin
- Max percent exposure per ticker (e.g., 20–30%)
- Max sector exposure (25–40%)
- Max position size based on notional portfolio value
- Synthetic delta limits (from LEAPS)
- No leveraged ETFs
- Drawdown throttling:  
  - If portfolio DD > 10%, reduce call selling frequency
  - If DD > 15%, stop opening new positions

Additionally:
- All strikes & expirations validated pre-trade
- Automated prevention of assignment risks
- All orders pass TFSA filters before reaching IBKR

---

# 4. TFSA Strategy Engine Flow

1. Identify long stock or LEAPS.
2. Determine eligible CC candidates.
3. Apply risk constraints.
4. Select strikes using delta target.
5. Generate Recommendations.
6. Store recommendations → display in UI.
7. When Phase 2.5 is complete → trade execution allowed.

---

# 5. Expected Performance Characteristics

| Strategy                  | Expected ROR | Volatility | Drawdown   |
|---------------------------|--------------|------------|------------|
| Covered Calls (Stock/ETF) | 8–15%        | Low        | 5–12%      |
| Covered Calls (LEAPS)     | 12–25%       | Medium     | 10–20%     |
| Cash-like ETFs + CC       | 5–10%        | Very low   | 3–7%       |
-----------------------------------------------------------------------

# 6. Future Enhancements

- TFSA Momentum ETF Rotation Module  
- TFSA Optimization with AI Allocation Engine  
- TFSA Regime Switching (switch CC frequency)  
- TFSA Auto-hedging via long puts (optional)  

---

# 7. Integration With Main System

TFSA module uses:
- StrategyEngine core  
- RecommendationEngine core  
- OrderManager (Phase 2.5)  
- TFSA-specific RiskEngine variant  
- TFSA dashboards in React UI  

These strategies do **not** interact with PM-based risk rules.

---

# 8. Deployment Timing

This module is implemented in:

👉 **Phase 2.5** (after Phase 2 core auto-trading for PM accounts is stable)

---

End of Document.
