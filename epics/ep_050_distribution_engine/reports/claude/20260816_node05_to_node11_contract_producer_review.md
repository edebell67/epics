# EP050 Node 05 → Node 11 Contract — Producer-Side Review Artifact

> VERSION HISTORY
> - v1.0.0 · 2026-08-16 · Initial versioned producer review with executed JSON-schema validation evidence, superseding the board-only review reply.

**Reviewer (producer side):** Claude, Node 05 (Search Demand Discovery) owner within EP050 Nodes 01–10.
**Reviewed artifact:** `epics/ep_050_distribution_engine/integration/proposals/gemini/20260816_node10_to_node11_contract_proposal_v1.md`, v1.1.0.
**Board thread:** initial review `20260816T203241450_claude_411400e6`; Gemini's v1.1.0 revision `20260816T204037424_gemini_c2faf9cd`; Codex's request for a review artifact plus lifecycle evidence `20260816T204220995_codex_0f46c781`.
**Decision boundary:** This is a producer-side compatibility review, not MVP approval or canonical contract promotion. No `implementation/node_NN/` folder was touched; no live network/external call was made.

## Review Findings (v1.0.0, against original proposal)

1. **Schema alignment:** `DemandSignalPayload` fields (`topic`, `raw_query`, `source_type`, `observed_at`, `geography`, `service_context`) correctly match what Node 05's manually-curated raw-signal fixture, as described in `reports/claude/20260816_ep050_nodes_01_10_mvp_classification.md`, would actually produce.
2. **Producer mislabel:** original v1.0.0 named the producer as "Node 05 Curated Search Signal / **Node 10 Trend Output**," but Node 10 (Trend Detection) was explicitly classified **D** and deferred out of the MVP candidate in the Claude Nodes 01–10 report — it needs accumulated multi-date signal history a single-seed MVP will not have, and the payload itself carries no trend/velocity fields. Recommended relabeling to Node 05 only, so canonical promotion would not silently re-admit Trend Detection to MVP scope.
3. **Source-type scope drift:** `source_type` enum listed `search_query` and `forum_question` as valid values alongside `manual_curation`/`synthetic_fixture`, despite the field description and the confirmed no-live-collection boundary for this allocation restricting the MVP to manual/synthetic sources only. Recommended pinning the enum to the two MVP-valid values and treating the other two as reserved for a future, separately-authorized live phase.

## Gemini's v1.1.0 Revision — Verified

Both findings were addressed in v1.1.0:
- Producer line now reads "Stage 2 / Claude (Node 05 Curated Search Demand Discovery Signal)" — Node 10 no longer referenced.
- `source_type` enum is now `["manual_curation", "synthetic_fixture"]`, with the description explicitly noting `search_query`/`forum_question` are "reserved for future authorized live phases."

## Executed Validation Evidence

Schema and seed fixture were extracted verbatim from the v1.1.0 proposal's two `json` code blocks and validated with the `jsonschema` library (v4.26.0):

```
Command: python -c "jsonschema.validate(instance=fixture, schema=schema)" against the extracted schema.json/fixture.json
Result 1 (positive): PASS — valid fixture conforms to schema
Result 2 (negative, scope-drift regression): PASS — source_type="search_query" correctly rejected: "'search_query' is not one of ['manual_curation', 'synthetic_fixture']"
Result 3 (negative, fail-closed rule #3): PASS — fixture with `geography` removed correctly rejected: "'geography' is a required property"
```

All three checks passed on the first run. No schema or fixture edits were required. No network call was made; validation ran entirely against the two extracted local JSON blocks.

## Producer Sign-Off

**Approved.** The Node 05 → Node 11 contract v1.1.0 is compatible with the Node 05 producer's expected output shape, both review notes are correctly resolved, and the pinned `source_type` enum is confirmed to fail closed against out-of-scope live-collection values. Ready for Codex canonical promotion, subject to the standard combined-MVP approval gate.
