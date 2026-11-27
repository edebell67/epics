<!--
  epics/ep_064_business_solutions/agent_04_collector/README.md — Collector agent demo: usage, links, lead capture

  VERSION HISTORY
  v1.0.0 · 2026-11-27 · Initial version.
-->
# EP064 · Agent 4 of 5: Collector (invoice, chase, get paid)

This is the agent version of ChaseUp (`app_01_chaseup` stays as the dashboard version). It's a self-contained `index.html` that plays two weeks in about a minute.

## What it shows
- Invoices are raised the moment Closer hands over a job (deposit, then the balance on completion) and sent with a card payment link.
- Payments are matched from the bank feed and the customer is thanked automatically.
- A business client 22 days late gets a firm reminder with statutory interest (11.75%) and fixed compensation, replies with a promise to pay, and chasing pauses until that date.
- A private customer part-pays and asks to spread the rest, so Collector agrees a payment plan within the owner's rules.
- **One judgement call:** the business client paid but left off the interest. Waive it or chase it? On the default setting it goes with "waive" after a countdown.
- A 61-day debtor gets a formal-letter warning and pays two days later. A real letter before claim would need the owner's OK.
- The finished job's balance is paid by card, and the customer is handed to Keeper.
- **Overview:** invoice list with status badges, money in from the bank feed, effort meter, activity log.

## Settings
`auto=0` Ask me first · `auto=1` Only ask on judgement calls (default, 0–1 taps per fortnight) · `auto=2` Just do it. Other parameters are the same as the other agents (`biz`, `name`, `sector`, `src`, `cid`, `hire=1`).
