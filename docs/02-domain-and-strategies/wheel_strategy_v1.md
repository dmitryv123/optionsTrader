# Wheel Strategy v1

## Purpose

Short puts on quality underliers, with controlled risk, aiming for steady theta with strong downside management.

## Config Fields

- `put_days_out` – Target days to expiry for new short puts.
- `put_delta_target` – Target option delta for entries.
- `universe` – List of eligible tickers.
- `max_positions` – Optional limit on open wheel positions.
- `max_notional_per_underlier` – Risk guard per symbol.

## Runtime Behavior

1. Load `StrategyContext` (cash, buying power, positions, executions).
2. Screen universe.
3. For each candidate, propose short put if:
   - within delta + DTE bands
   - passes all risk checks (cash, buying power, existing exposure).
4. Emit:
   - diagnostics
   - opportunities
   - recommendations
