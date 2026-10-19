<!--
  epics/ep_064_reddit_oppourtunity/ui_02_trader_risk_guard/README.md — Documentation for ApexGuard mobile-first trading demo UI
  
  VERSION HISTORY
  v1.0.0 · 2026-10-18 · Initial version: documents Reddit trading pain points T1+T2, mobile-first design, and interactive scenarios.
-->
# EP064 · UI 02: ApexGuard — Prop-Firm Drawdown/Tilt Guard & Multi-Strategy Correlation Monitor

## Reddit Pain Points Addressed
1. **T2 · Prop-Firm Trailing Drawdown & Behavioral "Tilt" Lockout (`r/FuturesTrading`, `r/Daytrading`)**:
   - Side-by-side tracking of **Intraday High-Water-Mark (HWM)** vs **End-of-Day (EOD)** trailing drawdowns across copy-traded accounts.
   - Real-time behavioral Tilt Gauge (0–100) monitoring order cadence, lot-size escalation, consecutive losses, and rapid re-entry after a loss.
   - Pre-breach automatic lockout & 1-click **Flatten & Lock All** to sever the copy-trader before a cascading drawdown blows multiple accounts.
2. **T1 · Multi-Strategy Correlation Spikes & Choppy Regime Bleed (`r/algotrading`)**:
   - Live 6-strategy equity curve overlay + 30-bar rolling pairwise correlation matrix ($\rho$).
   - Efficiency-Ratio & ATR percentile regime classifier (`TRENDING`, `CHOPPY`, `VOLATILE`).
   - 1-click **Auto De-Risk Cluster** and per-strategy `BOTH` / `BUY_ONLY` / `SELL_ONLY` directional filters.

## Mobile-First Design
- Designed for 375px–430px phone screens first (fixed bottom navigation bar, horizontal scenario chips, touch-friendly account cards, stacked responsive tables, bottom-sheet walkthrough modal) and scales up at `700px` and `1100px`.

## Launching the Demo
Run `run_demo.bat` or open `index.html` directly in any browser.
