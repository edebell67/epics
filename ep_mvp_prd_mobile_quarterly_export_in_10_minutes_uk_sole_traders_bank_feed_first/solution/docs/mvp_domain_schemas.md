# MVP Domain Schemas [V20260316_A1]

This document defines the canonical MVP domain contract for the UK sole-trader quarterly export product.

Machine-readable source of truth: `ep_mvp_prd_mobile_quarterly_export_in_10_minutes_uk_sole_traders_bank_feed_first/solution/backend/src/models/mvp_domain_schemas.json`

## Scope

The contract covers:

- canonical entity definitions for onboarding, bank ingestion, classification, evidence, quarter readiness, and merchant rules
- the fixed MVP category taxonomy and separate tag set
- nullable and blocker rules required for Finish Now and export gating
- Quarterly Pack CSV and PDF field mappings

## Category Taxonomy

Categories are export-facing and stable:

- `INCOME_SALES`
- `INCOME_OTHER`
- `EXP_COGS`
- `EXP_SUBCONTRACTORS`
- `EXP_TRAVEL`
- `EXP_VEHICLE`
- `EXP_MEALS`
- `EXP_ACCOM`
- `EXP_RENT_UTIL`
- `EXP_COMMS`
- `EXP_SOFTWARE`
- `EXP_MARKETING`
- `EXP_INSURANCE`
- `EXP_BANK_FEES`
- `EXP_PROFESSIONAL`
- `EXP_OFFICE`
- `EXP_TRAINING`
- `EXP_MISC`

Tags are not categories and must remain separate:

- `PERSONAL`
- `REVIEW_REQUIRED`

## Entity Summary

| Entity | Purpose | Critical Fields |
| :--- | :--- | :--- |
| `User` | Product identity and auth anchor | `user_id`, `email`, `auth_provider` |
| `BusinessProfile` | Sole-trader business context | `business_type`, `trading_name`, `tax_country`, `base_currency` |
| `BankAccount` | Read-only Open Banking account | `provider_account_id`, `provider_name`, `status`, `last_synced_at` |
| `BankTransaction` | Imported transaction source of truth | `txn_id`, `date`, `merchant`, `amount`, `direction`, `duplicate_flag`, `source_hash` |
| `TransactionClassification` | User-editable categorisation and blocker state | `category_code`, `business_personal`, `is_split`, `split_business_pct`, `confidence`, `duplicate_resolution`, `audit_trail` |
| `Evidence` | Receipt or invoice capture record | `type`, `captured_at`, `doc_date`, `storage_link`, `extraction_confidence` |
| `EvidenceLink` | Confirmed or deferred evidence matching outcome | `bank_txn_id`, `link_confidence`, `user_confirmed`, `confirmed_at`, `method` |
| `Quarter` | Quarter selection and export boundary | `period_start`, `period_end`, `quarter_label`, `status` |
| `QuarterMetrics` | Export gating and blocker ordering | `total_txns_in_period`, `blocking_txns_count`, `readiness_pct`, `blocking_queue` |
| `Rule` | Merchant default rule | `merchant_pattern`, `category_code`, `default_business_personal`, `default_split_business_pct` |

## Blocking And Nullable Rules

- Export is blocked when `category_code` is null.
- Export is blocked when `business_personal` is null.
- Export is blocked when `is_split = true` and `split_business_pct` is null.
- Export is blocked when `duplicate_flag = true` and `duplicate_resolution` is null.
- Missing or unmatched evidence is explicitly non-blocking.
- `category_code`, `business_personal`, `split_business_pct`, `duplicate_resolution`, and `EvidenceLink.bank_txn_id` all have documented nullable conditions in the JSON contract.

## Classification Audit Requirement

Any user-editable classification mutation must append an `audit_change_entry` with:

- `field_name`
- `changed_at`
- `changed_by`
- `previous_value`
- `new_value`

This requirement applies to category changes, business/personal decisions, split percentage edits, and duplicate resolution changes.

## Relationship Notes

- One `User` owns one `BusinessProfile` in the MVP.
- One `BusinessProfile` can connect many `BankAccount` records.
- One `BankAccount` imports many `BankTransaction` records.
- One `BankTransaction` has one current `TransactionClassification`.
- `Evidence` and `BankTransaction` are connected through `EvidenceLink` so matching remains confirm-first and auditable.
- One `Quarter` has one current `QuarterMetrics` snapshot.
- `Rule` suggestions can prefill `TransactionClassification`, but user edits still write to the same auditable contract.

## Quarterly Pack Contract

The JSON contract maps every field from the epic:

- `Transactions.csv` includes all 14 required columns, preserving epic order.
- `EvidenceIndex.csv` includes all 10 required columns, preserving epic order.
- `QuarterlySummary.csv` includes all 8 required columns, preserving epic order.
- `QuarterlyPack.pdf` defines required summary sections for downstream implementation.

## Validation

Executable validator: `ep_mvp_prd_mobile_quarterly_export_in_10_minutes_uk_sole_traders_bank_feed_first/solution/backend/validate_mvp_domain_schemas.js`

It verifies:

- all MVP entities exist
- category codes match the epic list exactly
- tags remain separate from categories
- blocking and nullable fields are represented
- audit fields exist for classification edits
- Quarterly Pack contracts match the required field order
