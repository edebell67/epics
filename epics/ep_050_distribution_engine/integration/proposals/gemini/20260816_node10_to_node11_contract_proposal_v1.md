# EP050 Stage 2 -> Stage 3 Interface Contract Proposal (Node 05 -> Node 11)

> VERSION HISTORY
> - v1.1.0 · 2026-08-16 · Ingested Claude producer feedback: clarified producer as Node 05 (Search Demand Discovery) and pinned MVP source_type enum.
> - v1.0.0 · 2026-08-16 · Initial versioned proposal for Stage 2 to Stage 3 boundary contract.

**Producer:** Stage 2 / Claude (Node 05 Curated Search Demand Discovery Signal)  
**Consumer:** Stage 3 / Gemini (Node 11 Intent Classification)  
**Status:** Proposal (Reviewed & Approved by Claude Producer in board event `20260816T203241450_claude_411400e6`)

---

## 1. Schema Definition (JSON / Pydantic Model)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "DemandSignalPayload",
  "type": "object",
  "required": [
    "signal_id",
    "target_id",
    "raw_query",
    "topic",
    "source_type",
    "observed_at",
    "geography",
    "service_context"
  ],
  "properties": {
    "signal_id": {
      "type": "string",
      "description": "Unique deterministic identifier for the demand signal (e.g., sig_20260816_boiler_01)"
    },
    "target_id": {
      "type": "string",
      "description": "Registered target identifier matching Node 01 (e.g., tgt_boiler_repair_blackheath)"
    },
    "raw_query": {
      "type": "string",
      "description": "Raw search query, question, or problem text observed from demand discovery"
    },
    "topic": {
      "type": "string",
      "description": "Normalized topic keyword or category (e.g., boiler_pressure_loss)"
    },
    "source_type": {
      "type": "string",
      "enum": ["manual_curation", "synthetic_fixture"],
      "description": "Source origin of the signal; pinned to manual_curation or synthetic_fixture for offline MVP (search_query/forum_question reserved for future authorized live phases)"
    },
    "observed_at": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 timestamp with timezone offset"
    },
    "geography": {
      "type": "object",
      "required": ["locality", "region", "country"],
      "properties": {
        "locality": { "type": "string" },
        "region": { "type": "string" },
        "country": { "type": "string" }
      }
    },
    "service_context": {
      "type": "object",
      "required": ["service_name", "market_segment"],
      "properties": {
        "service_name": { "type": "string" },
        "market_segment": { "type": "string" }
      }
    },
    "metadata": {
      "type": "object",
      "additionalProperties": true
    }
  }
}
```

---

## 2. Seed Fixture Example (Synthetic Boiler Repair MVP)

```json
{
  "signal_id": "sig_20260816_boiler_press_01",
  "target_id": "tgt_boiler_repair_blackheath",
  "raw_query": "boiler pressure dropped to zero no hot water how to fix",
  "topic": "boiler_pressure_loss",
  "source_type": "manual_curation",
  "observed_at": "2026-08-16T19:00:00+01:00",
  "geography": {
    "locality": "Blackheath",
    "region": "London",
    "country": "UK"
  },
  "service_context": {
    "service_name": "boiler_repair",
    "market_segment": "domestic_plumbing"
  },
  "metadata": {
    "urgency_hint": "high",
    "curated_by": "claude_node05_mvp"
  }
}
```

---

## 3. Node 11 Ingestion Validation Rules

1. **Target Lineage:** Must reference an existing registered `target_id`.
2. **Deterministic Processing:** Given identical `signal_id` and `raw_query`, Node 11 outputs identical `IntentClassificationResult`.
3. **Fail-Closed:** Signals missing required geographical or service context fields are rejected to the error log without downstream propagation.
