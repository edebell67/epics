<!--
  epics/ep_064_business_solutions/agent_06_bookkeeper/README.md — Bookkeeper agent demo: usage and SiteLedger link

  VERSION HISTORY
  v1.0.0 · 2026-11-27 · Initial version.
-->
# EP064 · Agent 6 of 6: Bookkeeper (books & tax as you go)

The agent built on top of SiteLedger's receipts, job costing and Making Tax Digital features. It's a self-contained `index.html` that plays a month in about a minute.

## What it shows
- Receipts are snapped or forwarded, then read, coded to categories and allocated to jobs. An unclear one is matched using the diary.
- The bank feed is reconciled, with personal spend kept out of the business books.
- Mileage is logged from the diary at HMRC's 45p rate.
- Job profit is updated once costs are in, with a pricing tip on a low-margin job.
- A tax set-aside estimate is sent each month (clearly labelled as a rough guide for the accountant to confirm).
- **The quarterly Making Tax Digital update always needs the owner's OK**, in every mode including "Just do it". The owner can submit it or send it to their accountant first. That's 1 tap a month, about 1% of the work.
- **Overview:** spend by category, job profit, MTD status, effort meter and log. The trades version links to SiteLedger (`?play=tax`).

## SiteLedger links (trades only)
- Closer → `../ui_01_siteledger_quote_jobcost/index.html?play=workflow`
- Collector → `?play=inv`
- Bookkeeper → `?play=tax`
- Every agent's "All agents" tab notes that, for trades, the six agents work on top of SiteLedger.

The links are relative, so they work as long as the `agent_0x_*` folders sit next to `ui_01_siteledger_quote_jobcost`, both locally and on GitHub.
