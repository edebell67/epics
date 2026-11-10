<!--
  epics/ep_064_reddit_oppourtunity/ui_01_siteledger_quote_jobcost/README.md — Documentation for SiteLedger mobile-first demo UI
  
  VERSION HISTORY
  v1.2.0 · 2026-11-10 · Invoices tab (chase ladder), Tax tab (Making Tax Digital quarterly-update demo), scenario playback ?play=inv|tax.
  v1.0.0 · 2026-10-18 · Initial version: documents Reddit pain points B1+B2, mobile-first architecture, and demo walkthrough.
-->
# EP064 · UI 01: SiteLedger — Contractor Quote Follow-Up & Job-Cost Receipt Tracker

## Reddit Pain Points Addressed
1. **B1 · Estimate "Ghosting" & Follow-Up Fatigue (`r/smallbusiness`, `r/Contractor`)**:
   - Sequential quote numbering (`Q-0101` → `Q-0113`) that never drops continuity when converting to a job (`J-0041` → `J-0044`).
   - Automated aging badges (`Fresh`, `Due`, `Overdue`, `Ghosted`) based on configurable Day 3 / Day 7 / Day 14 follow-up rules.
   - 1-click SMS/Email follow-up modal with pre-filled placeholders (`{first}`, `{no}`, `{title}`, `{value}`).
2. **B2 · Field Receipt & Supplier Invoice Job-Costing (`r/Contractor`, `r/smallbusiness`)**:
   - Tap-to-scan sample thermal receipts or dictate/type voice notes (`"£140 at Travis Perkins for the Smith kitchen job"`).
   - Automatic supplier, VAT, and job matching with confidence scoring and live **Quoted vs. Actual Margin** impact preview before saving.
   - Unassigned receipt inbox for low-confidence or overhead receipts.

3. **B3 · Late-paying clients (`r/smallbusiness`, `r/smallbusinessowner`, `r/ausbusiness`)**: scan #2 idea #4, the most repeated small-business complaint ("Client owes me $3k and is 45 days late").
   - **💷 Invoices tab:** overdue invoices climb a 4-step ladder (days after due, editable: 0 / 7 / 14 / 30): friendly → firm → final notice → letter-before-claim warning. Each step has a template with `{first} {no} {amount} {due} {days} {interest}`.
   - Part payments; client reliability colour (worst lateness: ≤5 days green, 6–20 amber, 21+ red); average days to pay.
   - **Business clients only:** statutory interest at 8% over the Bank of England base rate (rate is a setting) plus fixed compensation of £40 / £70 / £100 by invoice size (Late Payment of Commercial Debts (Interest) Act 1998). Not applied to homeowners.
   - The last step only warns that a formal letter is coming; the UI notes that a real letter before claim to an individual must follow the Pre-Action Protocol for Debt Claims.
   - Jobs can raise an invoice for their uninvoiced balance; payments feed the Tax tab (cash basis).
4. **B4 · Making Tax Digital for Income Tax (`r/ContractorUK`, `r/freelanceuk`, `r/UKPersonalFinance`)**:
   - **🏛️ Tax tab, a DEMO not connected to HMRC.** SiteLedger isn't HMRC-recognised software; the page says so at the top. Per a trade-press report (AccountingWeb, unconfirmed on GOV.UK), HMRC isn't granting new production access for 2026/27.
   - Mandate check (2024/25 qualifying income £78,400 > £50,000 → in from 6 Apr 2026; £30k from Apr 2027, £20k from Apr 2028).
   - 2026/27 quarter deadlines (7 Aug / 7 Nov / 7 Feb / 7 May) and the final declaration (31 Jan 2028).
   - **Cumulative year-to-date** figures per quarter, built from digital records: bank import, scanned receipts and invoice payments (cash basis, not VAT-registered). Expenses are grouped into HMRC-style categories with record counts.
   - Readiness checks: uncategorised transactions block "Prepare". "Prepared" means not sent.

## Scenario playback (v1.2.0)
- **▶ Invoice chase ladder** (`?play=inv`, 8 steps):
  1. Friendly reminder to Lucy Grant (2d overdue) and a firm reminder to Sarah Smith (part-paid).
  2. Final notice to Khan Stores Ltd with statutory interest (£17.36 for 22d at 12% + £70).
  3. Letter-before-claim warning to Ben Carter (61d).
  4. +3 days: 2 invoices paid, outstanding £10,455 → £6,405.
  5. +7 days: the ladder advances on its own.
- **▶ MTD quarterly update** (`?play=tax`, 7 steps): why the business is in → deadlines → Q2 year-to-date figures (turnover £42,380) → check fails on an uncategorised £86.40 Amazon payment → categorised → prepared (not sent).
- Playback never overwrites the viewer's saved data (save() is skipped while playing), and the demo date moves with the scenario.
- Nav is now Home / Quotes / Jobs / Invoices / Receipts / Tax; follow-up and chase rules are under the "rules" links.

## Mobile-First Design
- Base CSS targets 375px–430px phone screens with a fixed bottom navigation bar, 44px minimum touch targets, horizontal swipeable receipt strips, stacked-card responsive tables (`table.rt`), and bottom-sheet modals.
- Scales up cleanly at `min-width: 700px` (tablet) and `min-width: 1100px` (desktop multi-column layout).

## Launching the Demo
Run `run_demo.bat` or open `index.html` directly in any browser.
