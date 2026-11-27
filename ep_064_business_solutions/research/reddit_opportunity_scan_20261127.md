<!--
  epics/ep_064_business_solutions/research/reddit_opportunity_scan_20261127.md
  — Third Reddit pain-point scan: candidates for the cold-email prototype app campaign (after ChaseUp).

  VERSION HISTORY
  v1.0.0 · 2026-11-27 · Initial scan: ~20 web searches + 5 page reads, 7 ranked opportunities, 4 rejected, re-ordered build plan.
-->
# EP064 · Reddit opportunity scan #3 (2026-11-27)

Focus: small-business functions that suit a **self-contained prototype app** sent by cold email to UK trades, salons, garages and agencies, with a "request live access" button. This differs from scan #2, which mixed in trading tools.

## How this was gathered, and its limits
- reddit.com refused direct reads from both my page fetcher and the built-in browser. The evidence is therefore **search snippets plus published analyses of Reddit posts**:
  - IdeaFast: 160 recent r/smallbusiness posts, clustered and scored.
  - HiddenDrain: 100 top-voted posts from r/smallbusiness, r/EntrepreneurRideAlong and r/smallbusinessuk.
  - BigIdeasDB: complaints aggregated from Reddit, Capterra, G2 and Upwork.
  - Trade-software round-ups that quote r/Plumbing and r/restaurantowners threads.
- Upvote counts and thread dates were **not** checked for most items. Treat a theme as strong when several independent sources repeat it.
- Reddit announced in September 2026 that it would close its public API in November 2026 (Wikipedia, "Reddit API controversy"). Any automated Reddit monitoring in `reddit_fresh_thread_discovery_skill.md` should be checked, because it may stop working.
- Scoring (1–5 each): **Pain** · **Fit** (works as a cold-email demo for our four sectors, reuses ChaseUp's shell) · **Gap** (5 = few tools named) · **Build** (5 = small).

## Ranked shortlist

| # | App idea | Pain | Fit | Gap | Build | Total |
|---|---|---|---|---|---|---|
| 1 | **LeadDesk**: enquiry inbox + speed-to-reply + follow-up ladder | 5 | 5 | 3 | 4 | **17** |
| 2 | **QuickQuote**: 2-minute branded quote from a phone + quote follow-up | 5 | 5 | 2 | 4 | **16** |
| 3 | **Rebook + Renewals**: service/certificate due-date reminders, reviews, win-back | 4 | 5 | 3 | 4 | **16** |
| 4 | **CertWatch**: landlord / letting-agent compliance expiry tracker (CP12, EICR, EPC) | 4 | 3 | 2 | 5 | **14** |
| 5 | **RotaLite**: staff rota + hours log for cafés and salons | 4 | 3 | 1 | 3 | **11** |
| 6 | **TurnoverBoard**: holiday-let cleaner scheduling from booking calendars | 3 | 2 | 2 | 3 | **10** |
| 7 | **Monday Numbers**: weekly KPI sheet pulled from several tools | 4 | 2 | 3 | 1 | **10** |

### 1. LeadDesk: build next (moved ahead of Rebook)
**Pain:** following up leads is the #1 small-business problem in two separate analyses.
- IdeaFast scores "lead follow-up and team tracking" 92/100, its highest. Example thread: "Anyone else feel like follow-up is harder than actually getting leads?"
- In HiddenDrain's set, 22 of 100 top posts are about repeated manual chasing and follow-up.
- Trade marketers make the same case: leads come in, quotes go out, then the trail goes silent.

**Demo:** one inbox for web form, missed call, WhatsApp and Facebook enquiries. Each lead shows a speed-to-reply timer (going red after 5 min), an auto-reply on missed calls, a 3-touch follow-up ladder, and a pipeline running enquiry → quoted → won/lost with £ value lost to slow replies.
**Gap:** GoHighLevel resellers push "missed-call text-back" heavily, so the idea is known. Our angle: show the owner the **£ they lost last month** to slow replies, worked out from their own numbers.

### 2. QuickQuote
**Pain:** tradespeople want a quote out fast without paying for field-service suites.
- r/Plumbing (quoted by TradePicked): "I just need to send a clean looking quote with line items and my logo on it without it taking 20 minutes." The poster had rejected Jobber and ServiceTitan as overkill.
- Contractors complain about losing half a day to estimates that never turn into work. One plumber's quoting app emailed a bid to the wrong client.
- ServiceTitan users report roughly $235–$350 per tech per month.

**Demo:** pick the customer → add items from a saved price list (or type "boiler swap, 2 days, Worcester 30i") → logo'd PDF preview → send. Quote ageing then follows SiteLedger's Day 3/7/14 ladder. **Accept** turns it into a ChaseUp invoice, so the apps link up.
**Gap is low** (Jobber AI drafts, VoxTrade voice quotes, Tradify, Powered Now). Pitch it as "just the quote, nothing else".

### 3. Rebook + Renewals (reshape the planned Rebook app)
**Pain:** due dates live in spreadsheets and get missed. UK compliance content keeps repeating the same failure: "a gas safety certificate that expired three weeks ago because the renewal reminder was in a different spreadsheet."
**Reshape:** make **renewal reminders** the headline, ahead of review requests:
- Garages: MOT and service due.
- Gas engineers: annual boiler service and landlord CP12 (12 months).
- Electricians: EICR (every 5 years for rentals).
- Salons: rebooking interval per service.

Each reminder is a booked job, so the owner sees it as revenue, not admin. Keep review requests and lapsed-customer win-back as tabs 2 and 3.

### 4. CertWatch (landlords / letting agents)
The demand is real: there are several paid trackers (ExpiryTracker, ExpiryEdge, CertNudge) and free spreadsheets, and the rules are fixed (CP12 12 months, EICR 5 years, EPC 10 years). But the evidence is mostly vendor content rather than Reddit, and letting agents aren't in our four sectors. It works best as **a feature of #3** that gas engineers and electricians offer *their landlord customers*. Revisit as a standalone if we add property managers as a sector.

### 5. RotaLite
A restaurant owner on r/smallbusiness described three hours a week of manual scheduling after closing, plus a part-timer's hours that nearly went unrecorded. The market is crowded, though (RotaCloud, Deputy, Homebase, Schedulefly). Skip unless a salon lead asks for it.

### 6. TurnoverBoard
Hosts still schedule cleaners in spreadsheets and group chats. Turno, Breezeway, TurnoverPing and TurnoverBnB (free) already do it, and the audience is new to us.

### 7. Monday Numbers
"Every Monday I spend 3 hours pulling data from 4 different tools into a Google Sheet" (Capterra). The pain is real, but a self-contained demo can't connect to their tools, so the prototype would look fake. Skip.

## Rejected
- **Bookkeeping catch-up** ("our bookkeeper quit and we discovered 8 months of unreconciled transactions"): accounting liability; refer out.
- **Small-retail inventory** (3 shops sharing one Google Sheet): well served by inFlow and Zoho Inventory, and outside our sectors.
- **Trademark / IP disputes, tariffs, business debt:** high pain but not software problems.
- **Restaurant-owned reservations:** big incumbents, and outside our sectors.

## Cross-cutting finding: price it as "own it"
A summary of 9,363 recent Reddit posts reports growing pushback against stacking monthly subscriptions, with solopreneurs paying $100–300/month before earning anything. For the cold email and the live version, lead with **"set up for you, flat price, no per-user fees"** rather than another monthly SaaS. Our self-contained apps fit that pitch well.

## Recommended build order (revised)
1. ~~ChaseUp~~ (done, 2026-11-25)
2. **LeadDesk**: strongest evidence; it's what owners say hurts most.
3. **QuickQuote**: links ChaseUp and LeadDesk into "enquiry → quote → paid".
4. **Rebook + Renewals**: renewal reminders as the headline.

Together, 2–4 cover the whole money path for a trades business, so one cold email can link all three with "pick the one that hurts most".

## Sources
- IdeaFast, "Small Business Problems: What 160 Reddit Posts Reveal" — https://www.ideafast.pro/blog/small-business-problems-reddit
- HiddenDrain, "What 100 Small Business Owners Actually Complain About" — https://hiddendrain.com/blog/100-smb-reddit-posts-actually-complain
- BigIdeasDB, "Top Business Pain Points in 2026" — https://bigideasdb.com/business-pain-points-2026
- TradePicked, "The best plumbing software (2026)" — https://tradepicked.com/best/best-plumbing-software
- E. Larsen, "50 SaaS Ideas Pulled Straight from Reddit Pain Points" — https://medium.com/@e2larsen/50-saas-ideas-pulled-straight-from-reddit-pain-points-a64569371691
- Homebase, "Best Restaurant Scheduling Software in 2026" — https://www.joinhomebase.com/blog/best-restaurant-scheduling-software
- JustTaggit, "A simple system for landlord compliance reminders" — https://www.justtaggit.com/blog/landlord-compliance-reminder-system
- The Useful Daily, "The $300/Month Tax" — https://www.theusefuldaily.com/article/the-300-dollar-tax-subscription-rebellion
- Hook Agency, contractor follow-up — https://hookagency.com/blog/killers-of-contractor-follow-up-systems/
- Wikipedia, "Reddit API controversy" — https://en.wikipedia.org/wiki/Reddit_API_controversy
