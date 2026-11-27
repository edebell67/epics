<!--
  epics/ep_064_business_solutions/app_01_chaseup/README.md — ChaseUp prototype: usage, links for cold email, lead capture setup

  VERSION HISTORY
  v1.0.0 · 2026-11-25 · Initial version.
-->
# EP064 · App 01: ChaseUp — Invoice chasing prototype

Self-contained single-file app (`index.html`, no dependencies). This is a cold-email demo: the business opens it, sees what it does with sample data, then taps **Request access** to ask for the live version.

## What it does
- **Reminder ladder:** Friendly nudge (day 0) → Firm reminder (7) → Final notice (14) → Formal letter warning (30). Days, wording and channel (email / SMS / WhatsApp) can be edited on the Rules tab.
- **Late-payment interest:** business clients only. Statutory interest at 8% over the reference rate (3.75%, editable) plus £40 / £70 / £100 fixed compensation, worked out per invoice and added to reminders through `{statutory}`.
- **Payments:** part payments, pause/resume chasing, new invoices.
- **Client reliability:** green ≤5 days late, amber 6–20, red 21+, and average days to pay.
- **Sector presets:** trades, salons, garages, agencies, each with its own clients and invoices.

## URL parameters (use these in cold emails)
| Param | Effect |
|---|---|
| `biz=Westway%20Motors` | Header reads "Prepared for Westway Motors"; pre-fills the request form; used to sign off reminders |
| `name=Raj` | Pre-fills the contact's name on the request form |
| `sector=trades\|salon\|garage\|agency` | Sample data for that sector |
| `play=tour` | Starts the 11-step guided tour automatically |
| `src=email&cid=garages_nov26` | Campaign tagging, included in the lead email |
| `access=1` | Opens the request form on load |

Example email link:
`https://thetechprinciple.com/ep_064_business_solutions/app_01_chaseup/index.html?sector=garage&biz=Westway%20Motors&name=Raj&play=tour&src=email&cid=garages_nov26`

## Lead capture
- The **Request access** button (sticky bar, and the last tour step) POSTs to FormSubmit: `https://formsubmit.co/ajax/edward.bell@thetechprinciple.com`.
- **One-time activation:** the first request triggers an activation email from FormSubmit to that address. Click the link in it once; requests after that arrive as a table in your inbox. Do this yourself before the campaign goes out.
- After activation, FormSubmit gives you a random alias string. Replace the address in `CFG.formEndpoint` with it so your email isn't visible in the page source.
- Each lead email includes: name, business, email, phone, sector, invoices a month, message, `campaign_source`, `campaign_id`, `emailed_business`, the sector they viewed, whether they watched the tour, and the page URL.
- If the POST fails, the form offers a pre-filled `mailto:` link as a fallback.
- FormSubmit needs a web origin, so test from `serve_demos_lan.bat` (http://localhost:8064) or the live site, not by opening the file directly.

## Notes
- Demo only: no messages are sent. Sandbox changes are saved in the browser's localStorage. The tour never overwrites saved data.
- The formal-letter step only warns that a letter is coming. Real letters before claim to private customers must follow the Pre-Action Protocol for Debt Claims.
