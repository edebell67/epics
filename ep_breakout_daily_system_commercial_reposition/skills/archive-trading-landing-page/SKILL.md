---
name: archive-trading-landing-page
description: Use when editing or extending the Breakout Daily commercial landing page in ep_breakout_daily_system_commercial_reposition, especially when preserving the current dark institutional look, hero/ledger/archive/pricing/audit structure, and live product-data wiring.
---

# Archive Trading Landing Page

Use this skill when the task touches the landing page in `ep_breakout_daily_system_commercial_reposition`.

## Files

- App structure: `C:\Users\edebe\eds\ep_breakout_daily_system_commercial_reposition\solution\frontend\src\App.tsx`
- Visual system: `C:\Users\edebe\eds\ep_breakout_daily_system_commercial_reposition\solution\frontend\src\index.css`
- Product copy: `C:\Users\edebe\eds\ep_breakout_daily_system_commercial_reposition\solution\frontend\src\data\siteContent.ts`
- Live data: `C:\Users\edebe\eds\ep_breakout_daily_system_commercial_reposition\solution\frontend\src\data\generated\marketSnapshot.ts`
- Snapshot generator: `C:\Users\edebe\eds\ep_breakout_daily_system_commercial_reposition\solution\scripts\build-market-snapshot.mjs`

## Intent

The page should feel like a premium dark trading product:

- controlled, institutional, and dense
- strong blue-on-charcoal hero
- sharp grid alignment
- compact cards, not playful SaaS blocks
- real product data under the marketing shell

Do not collapse it back into a generic landing page or a simple utility table.

## Non-Negotiables

- Keep the overall section order:
  1. top nav + hero
  2. live performance ledger
  3. archive/product cards
  4. pricing
  5. audit/proof block
  6. footer/newsletter
- Preserve the dark visual language and spacing rhythm already established in `index.css`.
- Reuse live/generated data where possible instead of hard-coding fake performance content.
- If updating copy or products, keep the current look and feel intact.
- If changing layout rules, check that section-level centering does not break grid alignment.

## Content Rules

- Prefer real strategy-family labels derived from snapshot data over invented brand names.
- Prefer product tiers from `siteContent.ts` over placeholder pricing names.
- Keep compliance-sensitive copy restrained: research, signals, rankings, archives, proof. Avoid promises of guaranteed returns.
- Use concise headings and short support copy. The page should scan quickly.

## Editing Workflow

1. Read `App.tsx` and `index.css` first.
2. If content is the issue, patch `siteContent.ts` or the derived content logic in `App.tsx`.
3. If live data labels are poor, patch `build-market-snapshot.mjs` or the formatting helpers in `App.tsx`.
4. If layout is off, adjust `index.css` carefully and verify section alignment.
5. Run `npm run build` in `solution/frontend` after changes.

## Guardrails

- Do not replace the page with a Tailwind CDN mockup.
- Do not introduce bright multi-color accents.
- Do not add charts, carousels, or dashboard clutter unless explicitly requested.
- Do not widen text columns so far that the hero loses its poster-like composition.
- Do not change the current look and feel when the request is only about content/data.
