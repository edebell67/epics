<!--
  epics/ep_064_business_solutions/agent_02_frontdesk/README.md — Frontdesk agent demo: usage, links, lead capture

  VERSION HISTORY
  v1.0.0 · 2026-11-27 · Initial version.
-->
# EP064 · Agent 2 of 5: Frontdesk (answer, qualify, book)

A self-contained demo (`index.html`). It shows a busy Tuesday while the owner is out on a job. Seven enquiries come in through a missed call, voicemail, web form, WhatsApp, Facebook/Instagram and email; two of them were handed over by Scout.

## What it shows
- Every enquiry answered in under a minute. It asks the right questions and books the job into a free diary slot.
- Emergencies get a same-day slot and the owner is texted. Complaints get an apology and a free fix booked, and are flagged to the owner.
- Out-of-area work and services the business doesn't offer are turned down politely.
- **The owner is asked only when something is outside the rules** (e.g. commercial rates not on the price list). On the default setting a full day takes **0–1 taps**; if the owner doesn't answer, Frontdesk goes with the first option.
- Tap any enquiry to read the full customer conversation.
- **Always-on overview:** a pinned strip (answered, average reply, booked, needs you), plus an Overview tab with the diary Frontdesk filled, an effort meter, the channel mix, and the jobs handed to Closer (agent 3) for a written quote.

## Settings
`auto=0` Ask me first (every reply waits: about 7 taps a day, the trust-building mode) · `auto=1` Only ask if unsure (default) · `auto=2` Just do it.

## URL parameters
`biz`, `name`, `sector=trades|salon|garage|agency`, `auto`, `src`, `cid`, `hire=1` (same as Scout).

Example: `.../agent_02_frontdesk/index.html?sector=salon&biz=Studio%20Nine&name=Sam&src=email&cid=salons_dec26`

## Lead capture
"Put Frontdesk to work" POSTs to FormSubmit (`edward.bell@thetechprinciple.com`). The email includes the chosen setting, the demo tap count, whether they finished the day, and how many enquiries they say they miss each week.
