# Canonical Entity And Event Schemas [V20260311_A1]

This document defines the MVP canonical schema contract for `bizPA` quarterly capture, readiness, snapshot, and export workflows.

Machine-readable source of truth: `bizPA/backend/src/models/canonical_entity_event_schemas.json`

## Scope

The canonical model covers:

- all MVP monetary entities
- all MVP non-monetary entities
- immutable business events
- quarter reference rules
- export and snapshot field mappings

## Quarter Reference Convention

- Label format: `Q{quarter}-{year}`
- Allowed examples: `Q1-2026`, `Q2-2026`, `Q3-2026`, `Q4-2026`
- Validation pattern: `^Q[1-4]-\d{4}$`
- Assignment rule: derive from `transaction_date` using the tenant-local calendar date at commit time
- Immutability rule: once a monetary entity is committed, `quarter_reference` is not silently recomputed

## Monetary Entity Types

| Entity Type | Required Canonical Fields | Allowed Statuses | Included In Snapshot | Included In Export |
| :--- | :--- | :--- | :---: | :---: |
| `invoice` | `unique_id`, `entity_type`, `transaction_date`, `created_at`, `created_by`, `quarter_reference`, `counterparty_reference`, `description`, `category`, `net_amount`, `vat_amount`, `gross_amount`, `vat_rate`, `vat_type`, `status`, `commit_mode`, `source_type` | `composition`, `committed`, `sent`, `overdue`, `paid`, `partially_paid`, `voided`, `superseded` | Yes | Yes |
| `receipt_expense` | same monetary field set | `composition`, `committed`, `review_required`, `voided`, `superseded` | Yes | Yes |
| `payment` | same monetary field set | `composition`, `committed`, `allocated`, `unallocated`, `reversed`, `superseded` | Yes | Yes |
| `quote` | same monetary field set | `composition`, `committed`, `sent`, `accepted`, `expired`, `converted`, `voided` | Yes | Yes |
| `monetary_booking` | same monetary field set | `composition`, `committed`, `scheduled`, `completed`, `cancelled`, `superseded` | Yes | Yes |

### Monetary Validation Rules

- committed monetary entities must provide all monetary required fields
- unsupported `status`, `commit_mode`, `source_type`, and `vat_type` values must be rejected
- `quarter_reference` must match `Q1-YYYY` through `Q4-YYYY`
- committed monetary amounts are immutable after commit; correction must occur through new records and events, not in-place mutation

## Non-Monetary Entity Types

| Entity Type | Required Canonical Fields | Allowed Statuses | Included In Snapshot | Included In Export |
| :--- | :--- | :--- | :---: | :---: |
| `note` | `unique_id`, `entity_type`, `created_at`, `created_by`, `description`, `status`, `commit_mode`, `source_type` | `committed`, `archived` | No | No |
| `attachment` | `unique_id`, `entity_type`, `created_at`, `created_by`, `description`, `status`, `commit_mode`, `source_type` | `committed`, `linked`, `archived` | No | No |
| `booking` | `unique_id`, `entity_type`, `created_at`, `created_by`, `counterparty_reference`, `description`, `status`, `commit_mode`, `source_type` | `committed`, `scheduled`, `completed`, `cancelled`, `archived` | No | No |
| `client` | `unique_id`, `entity_type`, `created_at`, `created_by`, `counterparty_reference`, `description`, `status`, `commit_mode`, `source_type` | `active`, `inactive`, `archived` | Yes | No |
| `supplier` | `unique_id`, `entity_type`, `created_at`, `created_by`, `counterparty_reference`, `description`, `status`, `commit_mode`, `source_type` | `active`, `inactive`, `archived` | Yes | No |
| `reminder` | `unique_id`, `entity_type`, `created_at`, `created_by`, `counterparty_reference`, `description`, `status`, `commit_mode`, `source_type` | `committed`, `scheduled`, `completed`, `dismissed`, `archived` | No | No |
| `snapshot` | `unique_id`, `entity_type`, `transaction_date`, `created_at`, `created_by`, `quarter_reference`, `description`, `status`, `commit_mode`, `source_type`, `version_number`, `included_transaction_ids`, `totals`, `vat_totals`, `readiness_score`, `integrity_warning_summary`, `generated_files` | `generated`, `archived` | Yes | Yes |

## Immutable Business Event Types

All events require:

- `unique_id`
- `event_type`
- `created_at`
- `created_by`
- `source_type`
- `description`

Optional link and context fields:

- `linked_entity_id`
- `linked_entity_type`
- `quarter_reference`
- `status_from`
- `status_to`
- `metadata`
- `reason`

Supported `event_type` values:

- `entity_created`
- `entity_committed`
- `entity_status_changed`
- `entity_voided`
- `entity_superseded`
- `payment_recorded`
- `quote_converted`
- `snapshot_created`
- `quarter_closed`
- `quarter_reopened`
- `auto_commit_enabled`
- `auto_commit_disabled`
- `governance_policy_changed`
- `readiness_recalculated`
- `export_generated`

## Export And Snapshot Alignment

The field dictionary maps every canonical shared field to:

- an accountant/export package column name
- a snapshot payload field

This keeps the same canonical field set usable by:

- capture preview and commit
- tax readiness scoring inputs
- quarterly snapshot generation
- CSV or accountant-ready export packaging
- event timeline rendering

## Validation Implementation

Executable validator: `bizPA/backend/validate_canonical_schemas.js`

It currently verifies:

- all PRD monetary entity types are present
- all PRD non-monetary entity types are present
- missing required monetary fields are rejected
- unsupported lifecycle state values are rejected
- event types are recognized
- field dictionary entries map to both export and snapshot outputs

## Adoption Notes

- Use the JSON artifact for code and test references
- Use this document for implementation guidance and cross-team review
- Older docs focused on pre-quarterly capture models and should not be treated as the canonical contract for MVP quarterly flows
