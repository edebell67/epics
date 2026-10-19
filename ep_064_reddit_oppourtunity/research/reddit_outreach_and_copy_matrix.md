<!--
  epics/ep_064_reddit_oppourtunity/research/reddit_outreach_and_copy_matrix.md
  — Reddit value-first outreach strategy, comment-sniping search queries, and ready-to-post copy matrix for EP064 UI_01 (SiteLedger) and UI_02 (ApexGuard).

  VERSION HISTORY
  v1.0.0 · 2026-10-19 · Initial version (V20261019_0347): documents the Trojan-Horse Reddit outreach playbook, search queries, and copy templates.
-->
# EP064 · Reddit Value-First Outreach & Copy Matrix (`V20261019_0347`)

## 1. The 5 Golden Rules of Reddit "Anti-Marketing"

1. **Zero external links in the main post body**: Subreddits like `r/smallbusiness`, `r/Contractor`, `r/algotrading`, and `r/FuturesTrading` auto-remove posts containing external URLs from non-whitelisted accounts. Post **native screenshots, a 30-second screen recording (MP4/GIF), or pure breakdown text** first.
2. **Never put brand names in the post title**: Frame every title around a **painful problem, a quantitative post-mortem, or an open workflow question**.
3. **Give away the mechanism in the post**: Explain the exact rule/math (e.g., Day 3/7/14 ghosted-quote cadence, or Intraday HWM vs EOD buffer + Tilt Score formula) so readers get immediate value without clicking anything.
4. **Let comments ask for the link (or pin to profile)**: Only share the live demo URL when a commenter asks *"Can I try this?"*, or pin the demo hub to your Reddit profile and write *"Pinned the interactive mobile sandbox on my profile so I don't break sub rules."*
5. **9:1 Comment-to-Post Warmup**: Reply to 5–10 active complaint threads (Section 2) before publishing a standalone "Show & Tell" thread (Section 3).

---

## 2. Playbook A: Comment-Sniping Search Queries & Replies

Run these searches on Reddit sorted by **New** or **Past Week** to find high-intent users actively complaining about the exact pain point:

### UI 01 · SiteLedger (`r/Contractor`, `r/smallbusiness`, `r/Construction`, `r/sweatystartup`)
- **Search Queries**:
  - `site:reddit.com/r/Contractor OR site:reddit.com/r/smallbusiness "jobber" OR "housecall" "too expensive"`
  - `site:reddit.com/r/Contractor "ghosted" OR "following up" quotes OR estimates`
  - `site:reddit.com/r/Contractor "receipts" OR "job costing" spreadsheet`
- **Reply Template (No Link)**:
  > "Ran into the exact same wall—Jobber/Housecall wanted $150+/mo once you add techs, and basic invoicing apps lose the quote-to-job numbering trail (`Q-0101` → `J-0041`) and don't tell you when material receipts eat your quoted margin. I ended up building a stripped-back mobile web sheet for myself that just does two things: a Day 3 / Day 7 / Day 14 ghosted-quote nudge queue, and a voice-note receipt parser ('£140 at Travis Perkins for the Smith kitchen') that updates actual vs quoted job margin live. Happy to share the standalone HTML sandbox if you want to mess with it."

### UI 02 · ApexGuard (`r/FuturesTrading`, `r/Daytrading`, `r/algotrading`)
- **Search Queries**:
  - `site:reddit.com/r/FuturesTrading OR site:reddit.com/r/Daytrading "trailing drawdown" OR "intraday drawdown" blown OR apex`
  - `site:reddit.com/r/FuturesTrading "copy trading" OR "revenge trading" lockout`
  - `site:reddit.com/r/algotrading "correlation" OR "choppy" multiple strategies drawdown`
- **Reply Template (No Link)**:
  > "The biggest trap with intraday trailing drawdown (vs EOD) is when an unrealized spike pushes your High-Water Mark up and shrinks your actual buffer to <15% without you noticing—especially across 4–5 copy-traded accounts. Traditional journals only tell you after you're dead. I built a small pre-breach monitor that tracks real-time distance-to-floor (Intraday vs EOD) alongside a 10-minute cadence/size-escalation 'tilt score' that severs the copier before cascading breach. I have an interactive browser sandbox of it if you want to see the math."

---

## 3. Playbook B: "Roast My Workflow / Show & Tell" Post Templates

Attach the mobile screenshots from:
- `epics/ep_064_reddit_oppourtunity/ui_01_siteledger_quote_jobcost/evidence/screenshots/`
- `epics/ep_064_reddit_oppourtunity/ui_02_trader_risk_guard/evidence/screenshots/`

### Post 1 — `r/Contractor` & `r/smallbusiness` (SiteLedger)
- **Title**: `Got tired of losing £10k+ in ghosted quotes and finding faded receipts in the van, so I mocked up a dead-simple mobile tracker (no bloat). What am I missing?`
- **Body**:
  > Every CRM I tried was either built for a 50-van enterprise with a full-time office admin, or it was a basic PDF invoice maker that couldn't link sequential quotes (`Q-0104`) to actual job costs (`J-0041`).
  >
  > Two things were killing my margins:
  > 1. **Quote radio silence**: Sending a quote and forgetting to chase it on Day 3, Day 7, and Day 14 (the Day-14 "closing the file" message gets the highest reply rate).
  > 2. **Supply-house receipts**: Standing at Travis Perkins/Screwfix and not logging materials against the job budget until tax time—when it's too late to realize materials went 15% over budget.
  >
  > I put together a mobile-first single-page tracker (screenshots attached) where I can just dictate *"£140 at Travis Perkins for the Smith kitchen"* at the counter, and it matches the surname/job and shows the live margin impact before I even leave the car park.
  >
  > For other 1–5 person crews here: what’s the one thing in your quote-to-job-cost loop that still annoys you every week? (Happy to DM the standalone demo link if anyone wants to poke around it).

### Post 2 — `r/FuturesTrading` & `r/Daytrading` (ApexGuard Prop Tab)
- **Title**: `Visualizing the "Intraday HWM Trap" vs EOD Drawdown across 4 copy-traded accounts (+ a quantitative 'Revenge Tilt' lockout score)`
- **Body**:
  > Most blown prop evaluations happen from two things: forgetting that an unrealized profit spike raises your Intraday High-Water Mark floor, or going on a 10-minute revenge-trading spiral that cascades across all your copy-traded accounts at once.
  >
  > Traditional trade journals are post-mortems—they tell you why you blew the account *after* it's gone.
  >
  > I built a real-time risk guard prototype (screenshots attached) that calculates:
  > - **True Distance-to-Breach %**: Side-by-side Intraday HWM vs EOD floor across linked accounts.
  > - **Behavioral Tilt Score (0–100)**: Weighted from order cadence in the last 10 mins, lot-size escalation vs baseline, consecutive losses, and re-entry speed (<30s after a loss). At 75/100, it fires a hard lockout and severs the copier.
  >
  > For those running multi-account copiers: what behavioral triggers precede your worst drawdown days? Any metrics you'd add to the tilt formula?

### Post 3 — `r/algotrading` (ApexGuard Correlation Tab)
- **Title**: `How are you handling cross-strategy correlation spikes (ρ → 0.85) when the market shifts from Trending to Choppy?`
- **Body**:
  > We all build multi-strategy books assuming low historical pairwise correlation (ρ ≈ 0.15). Then a choppy/whipsaw regime hits, Efficiency Ratio collapses below 0.20, and suddenly 5 out of 6 sleeves enter synchronized drawdown at the exact same time.
  >
  > I've been testing a real-time regime + rolling 30-bar correlation guard (see screenshot) that:
  > 1. Flags when average pairwise ρ crosses `0.65` alongside ≥4 sleeves in simultaneous drawdown.
  > 2. Automatically pauses the highest-correlated momentum sleeves or flips directional filters (`BUY_ONLY` / `SELL_ONLY`) until ρ drops back below `0.30`.
  >
  > Curious how others here automate live de-risking when cross-strategy correlation spikes intraday—do you scale down size globally, or pause specific cluster members?

---

## 4. Subreddits That Allow Direct Demo Links Immediately
- `r/SideProject`
- `r/alphaandbetausers`
- `r/indiehackers`
- `r/smallbusiness` (Weekly "Promote Your Business" pinned thread only)
