<!--
  epics/ep_064_business_solutions/research/reddit_opportunity_scan_20261110.md
  — Second Reddit pain-point scan: candidates for the next EP064-style demo apps (after SiteLedger and ApexGuard).

  VERSION HISTORY
  v1.0.0 · 2026-11-10 · Initial scan: 25 Firecrawl searches over the past year, 8 ranked opportunities, 6 rejected.
-->
# EP064 · Reddit opportunity scan #2 (2026-11-10)

## How this was gathered
- 25 `site:reddit.com` searches through Firecrawl, limited to the past 12 months (`qdr:y`), about 6–7 threads each.
- **Limit:** Reddit blocks page scraping for Firecrawl and for my web search, so the evidence is thread titles and search snippets. Upvote and comment counts were **not** checked. A theme ranks higher when several separate threads in different subs raise the same complaint.
- Scoring (1–5 each): **Pain** (how often and how sharply it's raised) · **Fit** (reuses ApexGuard/SiteLedger code or your EP058 live data) · **Gap** (5 = few existing tools named in threads) · **Build** (5 = small demo, a few days).

## Ranked shortlist

| # | App idea | Pain | Fit | Gap | Build | Total |
|---|---|---|---|---|---|---|
| 1 | Prop Rulebook Guard: consistency rule + news windows | 5 | 5 | 4 | 5 | **19** |
| 2 | Edge Decay Monitor: is my strategy's edge gone, or is it the regime? | 4 | 5 | 4 | 3 | **16** |
| 3 | Prop Account Ledger: fees, resets, payouts, real net | 4 | 4 | 3 | 5 | **16** |
| 4 | Invoice Chase Ladder (SiteLedger module) | 5 | 4 | 2 | 5 | **16** |
| 5 | Sub COI Expiry Tracker (SiteLedger module) | 3 | 4 | 3 | 5 | **15** |
| 6 | Options Expiry Assignment Board | 4 | 3 | 4 | 3 | **14** |
| 7 | Scope Creep / Change-Order Log for freelancers | 4 | 3 | 2 | 4 | **13** |
| 8 | Supplier Price-Creep Tracker for restaurants | 3 | 2 | 4 | 3 | **12** |

### 1. Prop Rulebook Guard (consistency rule + news windows): recommended next
**Pain:** consistency rules (your biggest day can't exceed 30–50% of total profit) block payouts and catch traders out after a single good day. News-window rules wipe accounts over trades placed seconds before or after an event. Both come up repeatedly and angrily.
- r/LucidProp: "The consistency rule feels like a hostage situation" (50% rule: one $2,000 day forces you to keep trading).
- r/TopStepX: "Accidently went over the consistency rule, what should i do?"
- r/LucidProp: "Accidentally turned a 50% consistency violation into…"; "the consistency rule cost me a LucidFlex eval".
- r/PropFirmTester: "I keep seeing traders struggle with Apex's 30% rule"; "Which prop firm rule has actually hurt your trading the most?" (consistency named first).
- r/Forex: "Payout denial"; r/Daytrading: "Has a prop firm ever unfairly rejected your payout".
- r/propfirm: Alpha Futures "violated a news rule… break-even 1 minute 48 seconds after a news event"; r/Forex: "Please don't news trade in funded accounts! Lost 100k".

**Demo:** per account it shows the maximum you can still make today without breaking consistency, the profit you need to make that day compliant, and a countdown to the next restricted news window, with a warning if a position is open going into it. Playback scenario: "one big Monday blocks the Friday payout".
**Why first:** it slots into ApexGuard as a 5th tab and reuses its accounts, playback engine and floor chart. The same Reddit audience (r/FuturesTrading, r/Daytrading, r/PropFirmTester, r/LucidProp) and same launch kit apply. One thread mentions someone has built a consistency simulator, so the angle is "consistency + news + drawdown in one guard", not consistency alone.

### 2. Edge Decay Monitor
**Pain:** algo traders can't tell whether a strategy is broken or just in the wrong regime.
- r/algotrading: "Your strategy does not have an edge. It has an edge in one regime"; "Let's talk about regime detection"; "Regime detection metric"; "Regime change?" (breakout strategies 2010–17 vs 2018–25).
- r/Daytrading: "I can detect the market regime accurately. I still can't get it to fire the right strategy at the right time."

**Demo:** rolling expectancy per strategy, split by regime (ER/ATR bucket) and by side (BUY vs SELL). This ties in with your buy/sell-split Reddit post. It flags "decayed in all regimes" (retire) vs "only off-regime" (pause until regime returns).
**Edge over competitors:** it can run on **real** EP058/EP049 model data (live top_strategies), not mock data, which almost no Reddit-posted tool has. It's a bigger build because of the data plumbing.

### 3. Prop Account Ledger
**Pain:** multi-account prop traders lose track of challenge fees, resets and payouts, so they don't know whether they're actually up overall.
- r/PropFirmTester: "How do you track prop-firm challenges/resets/payouts?" (spreadsheet vs TradeZella vs Notion); "How are you guys handling taxes with multiple funded accounts".
- r/Daytrading: "I actually have a spreadsheet of all my accounts I need to keep…" ($83k payouts post); "+$1,418 copying trades across 17+ prop accounts".
- r/propfirm: "I built a free tool to track prop firm payouts and taxes" (and PropScaler is mentioned), so there are competitors.

**Demo:** net P&L after fees, ROI per firm, cost per funded account, breakeven payouts needed. Could be one tab in the same "prop suite" as #1. Leave out tax estimates (advice and liability risk).

### 4. Invoice Chase Ladder (SiteLedger module)
**Pain:** the most common complaint across the small-business subs.
- r/smallbusiness: "Client owes me $3k and is 45 days late" ("spending my entire friday afternoon just sending follow-up emails"); "Late-paying clients are killing my cash flow" (40% paid late); "How do you all handle chasing late-paying clients?"; "How do you actually handle clients who pay invoices late?"
- r/smallbusinessowner: "Chasing unpaid invoices is destroying my mental health"; r/ausbusiness: green/amber/red client scoring.

**Demo:** the same mechanic as SiteLedger's quote ghosting (Day 3/7/14 ladder), applied to invoices: overdue ageing, client reliability colour, late-fee calculator, one-tap polite→firm→final reminder. Cheap to build because it's a second tab in SiteLedger. Gap is low (Chaser, QuickBooks reminders, Xero exist), but it strengthens SiteLedger as "quote → job → paid".

### 5. Sub COI Expiry Tracker (SiteLedger module)
- r/GeneralContractor: "Wat do you use for subcontractor COI tracking" ("lot of spreadsheets and phone calls"; insurance premiums rise with poor compliance).
- r/ConstructionManagers: "How do you track subcontractor documents/insurance" (30/7/0-day reminders asked about); "go-to solution for insurance tracking".
- r/PropertyManagement: COI tracking for 200 tenants.

**Demo:** sub list with certificate expiry countdowns, "can't pay this sub until COI renewed" block, reminder ladder. Small; B2B buyers pay. Competitors: wardly.ai and CompliTrack were posted.

### 6. Options Expiry Assignment Board
- r/options: "Will I get assigned since my put landed at the money"; "Sold $649 QQQ calls… assigned in after-hours"; "Questions about managing assignment exposure"; defined-risk spreads confusion over pin risk.
- r/thetagang: "I had a put assignment voided".

**Demo:** expiring short legs within ±1% of the strike, after-hours move risk, cash or margin needed if assigned, "close or roll by 15:45" alerts. Needs an options chain or a broker import, so it's a mid-size build. It's a different audience from your futures/FX base.

### 7. Scope Creep / Change-Order Log
- r/freelance: "Lost $2,300 to scope creep on one project"; r/consulting: "one quick question… turns into 5 hours of unpaid work"; r/freelancing, r/web_design, r/graphic_design similar.

The gap is narrowing: ScopeKit launched on r/SideProject. It would only be worth doing as a contractor variation-order tab in SiteLedger.

### 8. Supplier Price-Creep Tracker
- r/restaurant: "Owners do you actually track when your distributors raise prices?"; food cost at 45% vs the 30–35% norm; r/Chefit: someone is building invoice-upload food costing.

Interesting, but outside your existing personas and data.

## Rejected (and why)
- **Trading journal:** saturated (several free journals posted every month).
- **Position sizing calculator:** saturated (several free PWAs and calculators posted).
- **Wash-sale tracker:** very high pain (r/options, r/tax, r/thetagang), but it's tax computation, carries liability, and a wrong number is costly. Don't build as a marketing demo.
- **UK MTD bridging spreadsheet:** timely (MTD for Income Tax started April 2026) and you're UK-based, but submitting to HMRC requires recognised software, and r/ContractorUK users are already building their own.
- **Salon no-show deposits:** commenters point out that booking apps already solve it.
- **Small-landlord rent tracking:** Stessa (free) dominates the replies.

## Recommended order
1. **Prop Rulebook Guard** as an ApexGuard tab with a playback scenario. It reuses the post, audience and site you've just deployed.
2. **Invoice Chase Ladder** as a SiteLedger tab (cheap, broad pain).
3. **Edge Decay Monitor** on real EP058 data. This is the most defensible of the eight, and the r/algotrading post can show real numbers.
