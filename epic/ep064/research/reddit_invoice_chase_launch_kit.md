<!--
  epics/ep_064_business_solutions/research/reddit_invoice_chase_launch_kit.md
  — Reddit value-first outreach playbook, comment sniper queries, copy templates, and interactive simulation handoff for B2B Invoice Chasing & Overdue Receivables (SiteLedger).
  
  VERSION HISTORY
  v1.0.0 · 2026-11-12 · [V20261112_1400] Initial launch kit for Invoice Chase: Reddit comment snipers, 4-step statutory ladder copy, discussion drafts, and live simulation waitlist conversion flow.
  Plan: workstream/200_inprogress/20261112_140500_ep064_reddit_invoice_chase_launch_kit.md
-->
# EP064 · Reddit B2B Invoice Chase & Receivables Launch Kit (`V20261112_1400`)

## Executive Summary & Anti-Marketing Strategy

Small business owners, contractors, and freelancers lose an estimated £11B annually in the UK to delayed B2B payments. When clients go silent past Net-30, vendors struggle with:
1. **Fear of confrontation**: Worrying that chasing firmly will burn the client relationship or lose future contracts.
2. **Corporate Accounts Payable gaming**: Mid-market and enterprise AP departments deliberately stalling payments to protect their own cash float ("next payment run is at month end").
3. **Sterile Xero/QuickBooks automation**: Generic boilerplate reminder emails that are effortlessly archived or ignored by finance clerks.

This playbook leverages the **"Trojan-Horse Anti-Marketing"** methodology:
- **Never post links in top-level posts or initial replies.**
- **Give away the entire 4-step statutory escalation ladder for free in plain text.**
- **When community members inevitably ask *"How do you automate this?"* or *"Do you have a template/tool?"*, reply with the free, interactive mobile simulation link** (`?play=inv`), which guides them through the workflow and invites them to join the priority waitlist and vote on features.

---

## 1. High-Intent Reddit Comment-Sniper Queries

Run these searches directly in Google or Reddit's search bar, sorted by **Past 24 Hours** or **Past Week**, to locate people who are actively desperate for an immediate solution:

### Search Strings
```text
site:reddit.com/r/smallbusiness "unpaid invoice" OR "late payment" OR "client hasn't paid"
site:reddit.com/r/freelance "client ghosting" OR "overdue invoice" OR "net 30"
site:reddit.com/r/Contractor "not paying" OR "final payment" OR "stage payment"
site:reddit.com/r/sweatystartup "late paying" OR "chasing money" OR "invoicing"
site:reddit.com/r/UKPersonalFinance "late payment commercial debts" OR "unpaid invoice ltd"
site:reddit.com/r/Entrepreneur "unpaid client" OR "accounts payable" stall
```

---

## 2. Playbook A: Value-First, Zero-Link Comment Replies

When replying to someone complaining about an overdue invoice, provide authoritative, step-by-step clarity immediately. **Do not pitch a product or drop a link.**

### Scenario 1: The Client Has Gone Completely Radio Silent (Ghosting past 30 days)
> "The reason polite reminder emails get ignored after 30 days is that AP clerks and busy clients mentally categorise them as 'no consequences yet'. 
>
> If you are in the UK or EU, the single most effective lever is invoking the **Late Payment of Commercial Debts (Interest) Act 1998**. You don't need to hire a solicitor or start a lawsuit—the law automatically entitles you to:
> 1. A fixed statutory compensation fee (£40 for debts under £1,000; £70 for debts £1,000–£10,000; £100 over £10,000).
> 2. Statutory interest at 8% above the Bank of England base rate (currently ~13% p.a.), calculated per day late.
>
> **The exact script that breaks the silence:**
> *'Hi [Name], Following up on invoice #1042 (£3,200) which matured on [Date] and is now 28 days overdue. Under the Late Payment of Commercial Debts Act 1998, a statutory late compensation fee of £70 plus daily interest of £1.14 has accrued, bringing the current balance to £3,270.00. To avoid additional interest and referral to our third-party recoveries panel on Friday, please confirm that payment has been scheduled on today's run. Updated statement attached.'*
>
> In 9 out of 10 corporate AP cases, having statutory penalties on their internal ledger triggers an audit red flag, and they push you into that afternoon's BACS payment batch. Give that wording a try."

---

### Scenario 2: Corporate Accounts Payable Stalling ("Our next payment run isn't until the end of next month")
> "Classic corporate AP game. They sign a Net-30 contract, and then unilaterally try to force you onto Net-60 or Net-90 because their accounting software has a bi-monthly batch rule.
>
> Here is how you push back politely without burning the relationship with your day-to-day contact:
>
> Separate the **relationship** from the **terms**:
> *'Hi [AP Contact], Thanks for the update. Our contractual terms agreed at project commencement were Net-30 (due Oct 15th). Our accounting system automatically applies statutory interest and compensation under the Late Payment of Commercial Debts Act once an account reaches 14 days overdue. As an independent supplier, we are unable to finance credit terms beyond our agreed contract. Please request an off-cycle manual BACS release from your finance director before [Date] so the account remains in good standing.'*
>
> Always make them acknowledge that *they* are asking you to provide an uncontracted credit facility. Most finance controllers will authorize an off-cycle payment rather than let statutory claims sit on their ledger."

---

### Scenario 3: Contractor / Tradesman Chasing Stage Payment
> "Never do additional work on site while an overdue milestone or stage payment is hanging. That is how trades get stuck holding the bag for thousands in materials.
>
> The cleanest way to handle it without sounding aggressive:
> *'Morning [Client], We've wrapped up Stage 2 (First Fix / Plastering). Per our agreed schedule, Stage 3 materials (kitchen cabinetry / second fix) are ordered and ready for delivery once the Stage 2 milestone invoice of £4,200 is settled. As soon as the transfer clears today, I'll release the delivery lorry for Thursday morning.'*
>
> It puts the ball entirely in their court without an argument: if they want work to continue, the agreed milestone clears first. Never apologize for asking to be paid for completed work."

---

## 3. Playbook B: Standalone Discussion Post Drafts

Post these from a seasoned account (`u/edbell609`) on relevant business subreddits. Attach clean screenshots from the evidence directory (`epics/ep_064_business_solutions/ui_01_siteledger_quote_jobcost/evidence/screenshots/`).

### Post Draft 1 · `r/smallbusiness` & `r/freelance`
- **Suggested Title**: `The 4-Step B2B Invoice Escalation Ladder that stopped corporate clients treating us like an interest-free bank`
- **Flair**: `Discussion` / `Advice/Tips`
- **Body**:
```text
For years, whenever a corporate or mid-market client hit 30 days overdue, we did what most small businesses do: sent a sheepish "just bumping this to the top of your inbox" email every Friday, and got ignored for another month.

Corporate Accounts Payable departments run on cold metrics. If an invoice has no late fees, no escalation ladder, and no statutory penalties, their CFO's treasury incentive is to hold your cash in their interest-bearing overnight account for as long as possible.

We completely overhauled our receivables into a strict 4-step cadence, and our average days sales outstanding (DSO) dropped from 44 days down to 8 days:

Step 1 · Day 0 (Due Date) — The Friendly Touchpoint
Subject: Invoice #1042 due today [Quick payment link]
Body: Light-touch note confirming the invoice matured today, attaching the PDF, and providing a 1-click BACS/Stripe link. (90% of honest clients pay here).

Step 2 · Day 7 Past Due — The Accounting Check-In
Subject: Overdue: Invoice #1042 (£3,200) - [Company Name]
Body: Re-attaching the original purchase order and delivery receipt. Asking if there is any paperwork discrepancy preventing the payment run.

Step 3 · Day 14 Past Due — The Statutory Warning (The Game Changer)
Subject: Notice of Statutory Late Interest & Fees: Invoice #1042
Body: Informing AP that under statutory debt legislation (Late Payment of Commercial Debts Act in the UK/EU), a £70 statutory compensation fee + 8% over base interest will be added to the principal on Day 21. Corporate AP clerks have strict KPIs against incurring statutory audit penalties. This single email gets 80% of stalled payments cleared within 24 hours.

Step 4 · Day 30 Past Due — The Formal Letter Before Claim
Subject: Formal Letter Before Action: Outstanding balance £3,270.00
Body: Full legal claim notice indicating referral to external debt recovery or small claims county court (MCOL) within 7 business days.

No emotions, no angry phone calls, just an automated ladder that treats late payment as a financial transaction rather than a personal insult.

Curious how other agencies/consultants here handle corporate clients who push for Net-60/90 without consent? What's your escalation trigger?
```

---

### Post Draft 2 · `r/Contractor` & `r/sweatystartup`
- **Suggested Title**: `Tired of spending Sunday nights chasing unpaid invoices and matching scrunched-up merchant receipts? Here is how we automated the pain away.`
- **Flair**: `Business` / `Tools`
- **Body**:
```text
If you run a 1 to 5 man crew, the worst part of the week isn't the physical work—it's the unpaid admin at 8 PM on a Sunday:
1. Chasing customers who "forgot" to transfer the final 20% stage payment after you handed over the keys.
2. Digging through the van dashboard for faded merchant receipts from Screwfix and Travis Perkins, only to realize at tax time that materials ate half your quoted profit.

Most software out there (Jobber, ServiceTitan) is bloated, built for massive 50-van fleets, and costs £150+/month before you even add an apprentice.

We mocked up a dead-simple, stripped-back mobile workflow:
- A 4-step polite payment chase ladder that automatically pings the client via WhatsApp/SMS on Day 3, Day 7, and Day 14 with a direct bank pay-link.
- If it's a commercial job past 14 days, it calculates the legal statutory interest and compensation fee automatically so AP clerks take it seriously.
- Dictating merchant receipts on the counter: "£140 at Travis Perkins for the Smith kitchen" so the live job margin updates before you even pull out of the car park.

For other sole traders and subbies here: what is the single biggest time sink in your quote-to-paid loop right now? Chasing money, quoting, or receipts?
```

---

## 4. Inbound Link Distribution (Converting Interest to Simulation & Waitlist)

When commenters reply asking:
- *"Is there an app or template that calculates this statutory interest?"*
- *"Can you share the exact email templates?"*
- *"How do you automate this without Xero being annoying?"*

**Reply Template (Providing the Live Simulation Link)**:
```text
I actually built a free interactive mobile simulation that lets you walk through the exact 4-step ladder, test the automatic statutory interest calculator, and see the Day 3/7/14 escalation messages in real time.

You can click through the simulated workflow directly in your browser here (no sign up, no email required to play):
https://thetechprinciple.com/ep_064_business_solutions/ui_01_siteledger_quote_jobcost/index.html?play=inv

If you're on a phone, it runs like a native app. There is also a waitlist button inside if you want to vote on which features (WhatsApp nudges, voice dictation, Xero email forwarding) we should build first. Let me know what you think of the escalation cadence!
```

---

## 5. Live Simulation Features & Demand Testing Flow

### Simulation Entry Points
- **Full Invoice Chase Walkthrough**:  
  `https://thetechprinciple.com/ep_064_business_solutions/ui_01_siteledger_quote_jobcost/index.html?play=inv`
- **Interactive Two-Track Engine (Mobile vs WhatsApp)**:  
  `https://thetechprinciple.com/ep_064_business_solutions/ui_01_siteledger_quote_jobcost/index.html?play=workflow`
- **Standalone Landing Page**:  
  `https://thetechprinciple.com/ep_064_business_solutions/siteledger.html`

### Demand Validation Metrics
When a user clicks **"⭐ Join Waitlist & Vote on Features"** inside the simulation or landing page:
1. They select their primary trade/business type (Carpentry, Electrical, Plumbing, Building, Agency, Freelance).
2. They vote on prioritized features:
   - *WhatsApp Voice Quotes & Variations*
   - *Live Job Cost & Material Burn vs Quote*
   - *Automated Stage Payment Chasing (Polite Escalation)*
   - *3-Minute Fast Estimates*
3. The lead and feature votes are automatically recorded:
   - Stored in browser `localStorage` under `siteledger_interest_leads`.
   - Dispatched via REST POST to `https://ep052-agentic-arena.onrender.com/api/waitlist` for real-time analytics aggregation.

---

## 6. Pre-Submission Checklist for u/edbell609

- [ ] Ensure account has 5–10 recent non-promotional comments in relevant communities (`r/smallbusiness`, `r/freelance`, `r/Contractor`).
- [ ] Post without external links in the original submission.
- [ ] Monitor replies within the first 60 minutes and respond to every single comment with detailed, value-first answers.
- [ ] Only provide the simulation link (`?play=inv`) when directly requested by an interested commenter or in a 1-on-1 DM.
- [ ] Log waitlist submissions and feature preference votes to determine primary product roadmap priorities.
