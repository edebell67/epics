# JSON Schema Definitions [V20260217_2345]

Superseded for MVP quarterly capture, snapshot, and export flows by `bizPA/backend/src/models/canonical_entity_event_schemas.json` and `bizPA/docs/canonical_entity_event_schemas.md`.

## 1. CaptureItem Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "id": { "type": "string", "format": "uuid" },
    "created_at": { "type": "string", "format": "date-time" },
    "type": { "enum": ["invoice", "receipt", "payment", "image", "note", "voice", "misc"] },
    "status": { "enum": ["draft", "confirmed", "reconciled", "archived"] },
    "amount": { "type": ["number", "null"] },
    "currency": { "type": "string", "default": "GBP" },
    "labels": {
      "type": "array",
      "items": { "type": "string" }
    },
    "client_id": { "type": ["string", "null"], "format": "uuid" },
    "job_id": { "type": ["string", "null"], "format": "uuid" },
    "extracted_text": { "type": ["string", "null"] },
    "raw_note": { "type": ["string", "null"] },
    "attachments": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "kind": { "enum": ["image", "pdf", "audio"] },
          "file_url": { "type": "string" },
          "metadata": { "type": "object" }
        }
      }
    }
  },
  "required": ["id", "type", "status"]
}
```

## 2. Sync Event Schema
Used for pushing local changes to the server.
```json
{
  "type": "object",
  "properties": {
    "event_id": { "type": "string", "format": "uuid" },
    "action": { "enum": ["create", "update", "delete"] },
    "entity_type": { "enum": ["capture_item", "client", "job", "calendar_event"] },
    "entity_id": { "type": "string", "format": "uuid" },
    "timestamp": { "type": "string", "format": "date-time" },
    "data_snapshot": { "type": "object" },
    "device_id": { "type": "string" }
  },
  "required": ["event_id", "action", "entity_type", "entity_id", "timestamp"]
}
```

## 3. Delta Response Schema
Used for pulling server-side changes to the client.
```json
{
  "type": "object",
  "properties": {
    "sync_token": { "type": "string" },
    "has_more": { "type": "boolean" },
    "changes": {
      "type": "array",
      "items": { "$ref": "#/definitions/SyncEvent" }
    }
  }
}
```
