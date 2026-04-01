# Core Entity Dictionary [V20260217_2345]

Superseded for MVP quarterly capture, snapshot, and export flows by `bizPA/backend/src/models/canonical_entity_event_schemas.json` and `bizPA/docs/canonical_field_dictionary.md`.

## 1. capture_items
Central object for all captured data. Supports offline-first flags and voice-specific metadata.

| Field | Type | Constraint | Description |
| :--- | :--- | :--- | :--- |
| id | UUID | PRIMARY KEY | Unique item identifier. |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Device creation time. |
| captured_at | TIMESTAMP | NULLABLE | User-confirmed or system-interpreted event time. |
| type | TEXT | NOT NULL | `invoice | receipt | payment | image | note | voice | misc` |
| status | TEXT | NOT NULL | `draft | confirmed | reconciled | archived` |
| amount | DECIMAL(18,8) | NULLABLE | Currency value. |
| currency | TEXT | DEFAULT 'GBP' | ISO 4217 code. |
| tax_flag | BOOLEAN | DEFAULT FALSE | Includes VAT/Tax. |
| vat_amount | DECIMAL(18,8) | NULLABLE | Extracted/assigned tax value. |
| due_date | DATE | NULLABLE | For invoices. |
| counterparty_id | UUID | NULLABLE (FK) | Reference to Client or Vendor. |
| client_id | UUID | NULLABLE (FK) | Link to Client entity. |
| job_id | UUID | NULLABLE (FK) | Link to Job entity. |
| extracted_text | TEXT | NULLABLE | OCR or Transcription result. |
| extraction_confidence | FLOAT | NULLABLE | AI model confidence score. |
| raw_note | TEXT | NULLABLE | User-typed or dictated notes. |
| location | TEXT | NULLABLE | Geo coordinates or address. |
| device_id | TEXT | NOT NULL | Source device identifier. |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last modification time. |
| voice_command_source_text | TEXT | NULLABLE | The transcript of the voice command that created this. |
| voice_action_confidence | FLOAT | NULLABLE | Intent confidence score. |

## 2. capture_item_labels
Pivot table for multi-tagging items.

| Field | Type | Constraint | Description |
| :--- | :--- | :--- | :--- |
| item_id | UUID | FK NOT NULL | Reference to `capture_items`. |
| label_name | TEXT | NOT NULL | e.g., 'Fuel', 'VAT', 'Chase'. |

## 3. capture_item_attachments
Reference to local or cloud-hosted files (images, audio, PDFs).

| Field | Type | Constraint | Description |
| :--- | :--- | :--- | :--- |
| id | UUID | PRIMARY KEY | Attachment identifier. |
| item_id | UUID | FK NOT NULL | Reference to parent `capture_items`. |
| kind | TEXT | NOT NULL | `image | pdf | audio` |
| file_path | TEXT | NOT NULL | Local filesystem or cloud URI. |
| metadata | JSON/TEXT | NULLABLE | e.g., dimensions, duration, checksum. |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Attachment creation time. |

## 4. clients
UK small trader customer records.

| Field | Type | Constraint | Description |
| :--- | :--- | :--- | :--- |
| id | UUID | PRIMARY KEY | Client identifier. |
| name | TEXT | NOT NULL | Customer display name. |
| phone | TEXT | NULLABLE | Primary contact number. |
| email | TEXT | NULLABLE | Primary contact email. |
| address | TEXT | NULLABLE | Service/Billing address. |
| consent_to_contact | BOOLEAN | DEFAULT FALSE | GDPR-required flag. |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Registration date. |
| last_contacted_at | TIMESTAMP | NULLABLE | Auto-updated by Revenue Engine actions. |

## 5. jobs
Service history entity for organizing work.

| Field | Type | Constraint | Description |
| :--- | :--- | :--- | :--- |
| id | UUID | PRIMARY KEY | Job identifier. |
| client_id | UUID | FK NOT NULL | Reference to `clients`. |
| service_category | TEXT | NULLABLE | e.g., 'Boiler Service', 'Tiling'. |
| status | TEXT | NOT NULL | `lead | quoted | booked | in_progress | completed | lost` |
| value_estimate | DECIMAL(18,8) | NULLABLE | Estimated job value. |
| next_due_date | DATE | NULLABLE | Re-servicing/follow-up target date. |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Job creation time. |

## 6. voice_events
History of all voice interactions for debugging and NLU tuning.

| Field | Type | Constraint | Description |
| :--- | :--- | :--- | :--- |
| id | UUID | PRIMARY KEY | Event identifier. |
| intent_transcript | TEXT | NOT NULL | What the user said. |
| intent_name | TEXT | NOT NULL | Classified intent (e.g., `capture_receipt`). |
| slot_data | JSON/TEXT | NULLABLE | Extracted slots (amount, date, client). |
| confidence | FLOAT | NOT NULL | AI confidence score. |
| action_result | TEXT | NOT NULL | `success | clarification_needed | failure | canceled` |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Event time. |

## 7. job_queue
Background processing tasks (OCR, ASR, Sync).

| Field | Type | Constraint | Description |
| :--- | :--- | :--- | :--- |
| id | UUID | PRIMARY KEY | Task identifier. |
| task_type | TEXT | NOT NULL | `ocr | transcription | sync_push | sync_pull` |
| item_id | UUID | FK NULLABLE | Reference to target item. |
| status | TEXT | NOT NULL | `pending | processing | completed | failed` |
| retry_count | INTEGER | DEFAULT 0 | Number of attempts made. |
| error_log | TEXT | NULLABLE | Details of failure. |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Task creation time. |
| run_at | TIMESTAMP | NULLABLE | Scheduled execution time. |

## 8. audit_events
Immutable audit log for security and action history.

| Field | Type | Constraint | Description |
| :--- | :--- | :--- | :--- |
| id | UUID | PRIMARY KEY | Audit identifier. |
| action_type | TEXT | NOT NULL | `create | update | delete | export | login` |
| entity_name | TEXT | NOT NULL | e.g., 'capture_items'. |
| entity_id | UUID | NOT NULL | ID of the affected record. |
| user_id | UUID | NOT NULL | User performing the action. |
| device_id | TEXT | NOT NULL | Device identifier. |
| diff_log | JSON/TEXT | NULLABLE | Snapshot of changes. |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Log entry time. |
