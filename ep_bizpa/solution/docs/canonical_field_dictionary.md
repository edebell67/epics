# Canonical Field Dictionary [V20260311_A1]

Authoritative machine-readable source: `bizPA/backend/src/models/canonical_entity_event_schemas.json`

| Field | Type | Applies To | Export Mapping | Snapshot Mapping | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `unique_id` | `uuid` | entities, events, exports, snapshots | `record_id` | `included_transaction_ids[]` | Immutable primary identifier for records and events. |
| `entity_type` | `string` | entities, events, exports | `entity_type` | `totals_by_entity_type` | Canonical entity label used across UI, export, and event layers. |
| `transaction_date` | `date` | monetary entities, snapshots, exports | `transaction_date` | `included_period` | Governs quarter assignment. |
| `created_at` | `datetime` | entities, events, snapshots | `created_at` | `created_at` | Audit timestamp for record or event creation. |
| `created_by` | `string` | entities, events, snapshots | `created_by` | `created_by` | User, owner, service account, or device-linked actor. |
| `quarter_reference` | `quarter_label` | monetary entities, snapshots, quarter-scoped events, exports | `quarter_label` | `quarter_label` | Must follow `Q{1-4}-{yyyy}`. |
| `counterparty_reference` | `string` | monetary entities, booking/client/supplier/reminder, exports | `counterparty_reference` | `counterparties[]` | Either a linked ID or a canonical human-readable fallback. |
| `description` | `string` | entities, events, exports, snapshots | `description` | `integrity_warning_summary` | User-facing summary text. |
| `category` | `string` | monetary entities, exports | `category` | `totals_by_category` | Export-friendly business category. |
| `net_amount` | `decimal(18,2)` | monetary entities, exports, snapshots | `net_amount` | `totals.net_amount` | Required on every committed monetary entity. |
| `vat_amount` | `decimal(18,2)` | monetary entities, exports, snapshots | `vat_amount` | `vat_totals.total_vat` | Required on every committed monetary entity. |
| `gross_amount` | `decimal(18,2)` | monetary entities, exports, snapshots | `gross_amount` | `totals.gross_amount` | Required on every committed monetary entity. |
| `vat_rate` | `decimal(5,2)` | monetary entities, exports | `vat_rate` | `vat_totals.by_rate` | Use the committed rate, not a recomputed live rate. |
| `vat_type` | `enum` | monetary entities, exports, snapshots | `vat_type` | `vat_totals.by_type` | Allowed values: `input`, `output`, `outside_scope`, `exempt`. |
| `status` | `enum` | entities, events, exports, snapshots | `status` | `entity_status_summary` | Allowed values depend on `entity_type`. |
| `commit_mode` | `enum` | entities, events, exports | `commit_mode` | `governance.commit_mode` | Allowed values: `manual`, `auto`. |
| `source_type` | `enum` | entities, events, exports | `source_type` | `capture_sources` | Allowed values: `voice`, `manual`, `attachment`, `import`, `system`. |

## Snapshot-Specific Required Fields

The `snapshot` entity adds:

- `version_number`
- `included_transaction_ids`
- `totals`
- `vat_totals`
- `readiness_score`
- `integrity_warning_summary`
- `generated_files`

## Quarter Reference Rule

- `transaction_date` on `2026-03-11` derives `quarter_reference = Q1-2026`
- `transaction_date` on `2026-07-04` derives `quarter_reference = Q3-2026`
- the derived label becomes part of the committed canonical record and must not be changed silently later
