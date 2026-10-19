<!--
  epics/ep_064_reddit_oppourtunity/ui_01_siteledger_quote_jobcost/README.md — Documentation for SiteLedger mobile-first demo UI
  
  VERSION HISTORY
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

## Mobile-First Design
- Base CSS targets 375px–430px phone screens with a fixed bottom navigation bar, 44px minimum touch targets, horizontal swipeable receipt strips, stacked-card responsive tables (`table.rt`), and bottom-sheet modals.
- Scales up cleanly at `min-width: 700px` (tablet) and `min-width: 1100px` (desktop multi-column layout).

## Launching the Demo
Run `run_demo.bat` or open `index.html` directly in any browser.
