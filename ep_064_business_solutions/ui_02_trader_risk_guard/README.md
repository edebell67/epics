<!--
  epics/ep_064_business_solutions/ui_02_trader_risk_guard/README.md — Documentation for ApexGuard mobile-first trading demo UI
  
  VERSION HISTORY
  v1.4.0 · 2026-11-10 · Rulebook tab (consistency + news-window rules) and playback ?play=rules.
  v1.3.0 · 2026-11-10 · Scenario playback (?play=hwm|tilt|corr), equity-vs-floor chart, computed tilt score and de-risk, EOD floor fix.
  v1.2.0 · 2026-11-02 · V20261102_0530: Added live EP058 Strategy Intelligence streaming integration (port 8149).
                        Dynamically selects top 4 models from PostgreSQL tradedb and monitors as prop trades.
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

## EP058 Strategy Intelligence Integration (Live Mode)
- **Service Endpoint**: Connects to the local EP058 FastAPI service on `http://127.0.0.1:8149`.
- **Dynamic 4-Model Selection**: Ingests `GET /api/top_strategies?days=10&limit=4&dedupe=true` to rank and select the 4 highest-performing active models from PostgreSQL `tradedb`.
- **Virtual Prop Account Mapping**: Evaluates each model under realistic prop-firm rules:
  - Model 1 $\to$ Apex \$50K Intraday Trailing Account (Evaluation 1)
  - Model 2 $\to$ Apex \$50K Intraday Trailing Account (Copy Account)
  - Model 3 $\to$ Topstep \$100K EOD Trailing Account (Funded Account)
  - Model 4 $\to$ MFFU \$50K EOD Trailing Account (Funded Account)
- **Live Stream / Sim Toggle**: Seamless 1-click toggle between real-time PostgreSQL streaming and offline stress-test simulation presets (*Intraday HWM trap*, *Revenge tilt lockout*, *Correlation spike*).

## 📏 Rulebook tab: Prop Rulebook Guard (v1.4.0)
Built from scan #2 (`research/reddit_opportunity_scan_20261110.md`, idea #1): consistency rules and news-window bans are the prop rules Reddit traders complain about most (r/LucidProp, r/TopStepX, r/PropFirmTester, r/propfirm).
- **Consistency rule** per account: biggest single day ≤ X% of the cycle's total profit. The tab shows:
  - **Can still make today:** `cons × prior profit ÷ (1 − cons)` minus today so far. Past this, today becomes the day that breaks the rule.
  - **Profit still needed for payout:** `max(target, biggest day ÷ cons) − total`. The tab labels whether the target or consistency is the binding number.
  - A daily P&L bar chart with a dashed "max allowed day" line. The day that breaks the rule is drawn red; today is blue.
  - State: `OK` / `NEAR CAP` (≤ max($100, 15% of today's cap) left) / `BLOCKED` / `READY`.
- **News rule** per account (±N minutes around each event): countdown to the next blackout, amber warning when a position is open within 5 minutes of it, red inside it.
- **Rule values are examples** (30% / 40% / 50%, targets, ±2 / ±5 min). The page says so; firms change their terms.
- **▶ Consistency + news rules** playback (9 steps, `?play=rules`):
  1. A position is closed at 08:27, before an 08:28–08:32 CPI blackout.
  2. The day reaches +$600, near the $686 cap.
  3. It closes at +$1,100, which is 40.7% of $2,700, so the payout is blocked and the bar rises to $3,667.
  4. Mon $3,050 and Tue $3,350 are both above the $3,000 target but still blocked.
  5. Wed $3,680 brings the big day down to 29.9%: READY.

## Scenario Playback (v1.3.0)
Viewers can watch exactly what ApexGuard does and how, without knowing where to tap:
- **▶ Intraday HWM trap** (9 steps): one copied trade runs to +$1,200 open, pulls back and closes at +$300. The Apex intraday floor ratchets up with the open peak, while the Topstep/MFFU EOD floors stay put. The next loser takes Apex to a 6% cushion, and the ≤15% rule flattens and locks both Apex accounts.
- **▶ Revenge tilt lockout** (7 steps): 3 losses, a 20s re-entry and size creeping from 1.5x to 2.5x. The score is built factor by factor (0 → 12 → 26 → 50 → 62 → 95). At 95 the 2.5x order is blocked, the copier is cut and all 4 accounts lock.
- **▶ Correlation spike** (6 steps): the regime moves from trending to choppy and the breakout cluster (S1, S2, S5) converges. The alert fires at 4 sleeves in sync drawdown with ρ 0.72, then Auto De-Risk pauses the cluster (ρ 0.72 → 0.56).
- Each step shows a caption, highlights the panel it is about, and switches to the right tab. On the Prop Guard tab an **equity vs trailing floor** chart is drawn as the scenario runs.
- Controls: ⏮ restart, ‹ › step, ▶/⏸, 1x/2x. Tapping any sandbox button leaves playback.
- Direct links: `index.html?play=hwm`, `?play=tilt`, `?play=corr` (autoplay).

### Rules (same in playback and sandbox)
| Rule | Value |
|---|---|
| Intraday floor | equity peak incl. open P&L − max DD |
| EOD floor | min(starting balance, closing-balance peak − max DD) |
| Auto-flatten + lock an account | cushion ≤ 15% of max DD |
| Tilt score | orders over 2 ×4 (max 30) + size over 1x ×16 (max 25) + losses in a row ×8 (max 25) + seconds under 30 on re-entry (max 20) |
| Tilt lockout (all accounts, 30 min) | score ≥ 75 |
| Correlation alert | ≥ 4 sleeves in sync drawdown and average ρ > 0.70 |
| Auto De-Risk | pause the highest-average-ρ sleeve, one at a time, until active ρ ≤ 0.60 |

## Mobile-First Design
- Designed for 375px–430px phone screens first (fixed bottom navigation bar, horizontal scenario chips, touch-friendly account cards, stacked responsive tables, bottom-sheet walkthrough modal) and scales up at `700px` and `1100px`.

## Launching the Demo
Run `run_demo.bat` or open `index.html` directly in any browser.
To start directly in live streaming mode, open `index.html?live=1`.
