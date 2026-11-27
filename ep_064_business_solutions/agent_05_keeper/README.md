<!--
  epics/ep_064_business_solutions/agent_05_keeper/README.md — Keeper agent demo: usage, links, lead capture

  VERSION HISTORY
  v1.0.0 · 2026-11-27 · Initial version.
-->
# EP064 · Agent 5 of 5: Keeper (repeat work)

A self-contained `index.html` that plays a month in about a minute.

## What it shows
- It checks the whole customer list for who's due (boiler service, colour, MOT, website check-up) and sends personal reminders with a self-booking link. About half book themselves in.
- Renewals are scheduled (landlord gas certificates, bride trials, fleet MOTs, domain/SSL renewals).
- **One judgement call:** next week has an empty day. Offer it as it is, or with a discount? On the default setting it offers it with no discount after a countdown.
- A gentle second nudge goes out, then Keeper stops so nobody's hassled.
- It checks back on a quote Closer lost 3 months ago. The customer is interested again and is handed back to Frontdesk, so **the chain loops**.
- **Overview:** diary fill for the next 4 weeks (about 51% → 85%), bookings by source, effort meter, activity log.

## Settings
`auto=0|1|2` and the same parameters as the other agents.

## Shared engine
Collector and Keeper are generated from `engine.js` plus one agent file each. If you want a sixth agent, it's mostly a new data file.
