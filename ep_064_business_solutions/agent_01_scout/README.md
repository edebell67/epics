<!--
  epics/ep_064_business_solutions/agent_01_scout/README.md — Scout agent demo: usage, links, lead capture

  VERSION HISTORY
  v1.1.0 · 2026-11-27 · Under-5%-effort design (daily plans, zero-tap default, pinned overview).
  v1.0.0 · 2026-11-27 · Initial version.
-->
# EP064 · Agent 1 of 5: Scout (lead generation)

A self-contained demo (`index.html`) of an AI agent that finds new work for a local business. It shows a simulated working week in a WhatsApp-style feed.

## The chain
Scout (find work) → Frontdesk (answer + book) → Closer (quote + follow-up) → Collector (get paid, = ChaseUp) → Keeper (repeat work).

## Design rule: owner effort under 5%
- One **daily plan** instead of approving each message. The default setting "Go ahead unless I stop it" needs **zero taps** a week.
- Optional: untick an item, edit the wording, hold the plan. "Ask me first" and "Just do it" modes are also available.
- **Always-on overview:** a strip pinned under the header (enquiries, possible work, reviews, needs you), plus an Overview tab with an effort meter (your taps vs Scout's tasks), lead sources, handover list and activity log.

## What Scout does in the demo
Win-back of lapsed customers, Google review requests (sent to everyone, never gated or incentivised), a Google Business Profile post, referral asks, and B2B intros to local companies (companies only, with opt-out). Results depend on what's approved or held. Enquiries are handed over to Frontdesk.

## URL parameters
| Param | Effect |
|---|---|
| `biz=Westway%20Motors` | Personalises the header, messages and CTA |
| `name=Raj` | Owner's first name, used in messages and to pre-fill the form |
| `area=Ealing` | Local area used in messages |
| `sector=trades\|salon\|garage\|agency` | Sample data |
| `auto=0\|1\|2` | Ask me first / Go ahead unless I stop it (default) / Just do it |
| `src=email&cid=garages_nov26` | Campaign tags, included in the lead email |
| `hire=1` | Opens the sign-up form on load |

Example: `.../agent_01_scout/index.html?sector=garage&biz=Westway%20Motors&name=Raj&area=Ealing&src=email&cid=garages_nov26`

## Lead capture
"Put Scout to work" POSTs to FormSubmit (`edward.bell@thetechprinciple.com`), the same setup as ChaseUp; the one-time activation still applies. The email includes the chosen autonomy level, what they approved in the demo, their tap count and whether they finished the week.
