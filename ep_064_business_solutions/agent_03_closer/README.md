<!--
  epics/ep_064_business_solutions/agent_03_closer/README.md — Closer agent demo: usage, links, lead capture

  VERSION HISTORY
  v1.0.0 · 2026-11-27 · Initial version.
-->
# EP064 · Agent 3 of 5: Closer (quote, follow up, win)

A self-contained demo (`index.html`). It plays two weeks of quoting in about a minute. Closer picks up the jobs Frontdesk handed over, plus one older quote.

## What it shows
- **Quote A** (from Frontdesk): built from the visit notes and the price list, with good/better/best options, sent within hours. The customer opens it 3 times, gets a short nudge and accepts the middle option. The job is booked, a 20% deposit link is sent, and it's handed to Collector.
- **Quote B** (business customer, custom pricing): the only thing that needs the owner. One tap, or it sends after a countdown because it's built from the rate sheet the owner approved in Frontdesk. The owner can change the price. It's followed up on day 7, approved, and handed to Collector.
- **Quote C** (older): day-3 follow-up, then the customer asks for a discount. Closer offers only a pre-approved alternative and never cuts the price itself. After the final follow-up it's lost, with the reason logged and a 3-month check-back handed to Keeper.
- **Always-on overview:** a pinned strip (quoted, won, win rate, needs you), plus an Overview tab with a quote board (draft / sent / following up / won / lost), an effort meter, lost reasons and an activity log.

## Settings
`auto=0` Ask me first (approve every quote) · `auto=1` Ask only on custom prices (default: 0–1 taps per fortnight) · `auto=2` Just do it.

## URL parameters
`biz`, `name`, `sector=trades|salon|garage|agency`, `auto`, `src`, `cid`, `hire=1` (same as the other agents).

## Lead capture
"Put Closer to work" POSTs to FormSubmit (`edward.bell@thetechprinciple.com`). The email includes the chosen setting, the demo tap count, quotes per month, and how they quote now.
