<!--
  epics/ep_064_reddit_oppourtunity/research/reddit_3day_repost_draft.md
  — Saved copy-paste post draft ready for re-submission once u/edbell609 account is seasoned.

  VERSION HISTORY
  v1.1.0 · 2026-11-10 · Refreshed: 25 Oct attempt blocked by new-account posting restrictions, rescheduled to Wed 11 Nov 13:00 GMT (UK left BST on 25 Oct);
                        dashboard line corrected — ApexGuard has no live Buy vs Sell split view, only distance-to-breach
                        and per-strategy BOTH/BUY_ONLY/SELL_ONLY filters; added alt title, link-request reply and pre-post checklist.
  v1.0.0 · 2026-10-22 · Saved verified de-AI'd human post draft for 3-day reminder.
-->
# Reddit Re-Post Draft (`u/edbell609`)

* **Target Subreddit**: `r/Daytrading` (primary) · `r/Forex` (fallback, don't cross-post the same day)
* **Scheduled For**: Wed 2026-11-11 13:00 GMT (08:00 ET, London session, before the NY open)
* **Flair**: `Discussion` (r/Daytrading) / `Forex` (r/Forex)
* **Links in body**: none (copy matrix rule 1)

---

## Pre-post checklist

The 25 Oct attempt was blocked by posting restrictions on the new account, so the risk this time is the same block, not the copy.

- [ ] Earn comment karma first: 5–10 genuinely helpful replies in r/Daytrading / r/Forex threads over the days before posting (copy matrix rule 5; no links, no mention of the dashboard)
- [ ] Re-read each subreddit's rules sidebar for minimum account age / karma and self-promotion limits; if `u/edbell609` is still under them, hold the post rather than trying again and getting flagged
- [ ] If both subs still block it, post first in a sub that accepts new accounts (`r/SideProject`, `r/alphaandbetausers`, copy matrix section 4) and keep this draft for later
- [ ] The 85% sell-side figure and the 35–40 pip London figure still match your own trade logs; change them if not

---

### Title
```text
Anyone else notice their "profitable" forex strategies are almost entirely carried by one side? (Buy vs Sell split)
```

Alt title (if the first gets no traction or for the r/Forex fallback):
```text
Split my strategy's closed trades into buys vs sells and the "winner" turned out to be a sell strategy with a losing long side attached
```

---

### Body
```text
Been digging into trade logs on EURUSD and GBP pairs over the last few weeks and noticed something that the overall backtest curve completely hides.

On paper one strategy looked like a solid winner. When I actually split the closed trades into Buy Net vs Sell Net, the Sell side was carrying something like 85% of the profit during the London slides, while the Buy side was mostly churning spread and taking death-by-a-thousand-cuts on false breakouts.

The other headache is London into the NY overlap. A setup will be up 35-40 pips floating in London, then NY open whipsaws right back through it. If you're on a funded account where the drawdown limit trails peak floating equity, you can give back half your cushion before you realise it.

I ended up putting together a quick mobile dashboard for myself that shows distance-to-floor live and lets me switch each strategy to buy-only or sell-only, so I'm not running the losing side out of habit or doubling lot size after a bad bounce.

For people running automated or rule-based forex setups: do you treat long and short rules as completely separate systems, or run the same logic both ways?
```

---

### Reply if someone asks for the dashboard

Only post the link when asked (copy matrix rule 4):
```text
Sure, it's a rough mobile sandbox with simulated accounts, nothing to sign up for. This link plays a 1-minute walkthrough of the floor creeping up on an intraday account: https://thetechprinciple.com/ep_064_reddit_oppourtunity/ui_02_trader_risk_guard/?play=hwm
On the Correlation tab you can tap a strategy's side label to switch it between both / buy-only / sell-only. Interested to hear what you'd want it to show.
```
URL checked 2026-11-10 after deploy `556a11d`: HTTP 200, serves ApexGuard v1.3.0, and `?play=hwm` autoplays the HWM trap walkthrough.
