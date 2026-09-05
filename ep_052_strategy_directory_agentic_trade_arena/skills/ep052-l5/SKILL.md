---
name: ep052-l5-implementation
description: Implement the EP052 l5 delivery scope when explicitly assigned, following its lean workflow and evidence gates; not a visiting-agent trading skill or agent runner.
---

<!-- VERSION HISTORY v1.0.0 · 2026-09-02 · Map-to-implementation guidance; runtime actions remain unimplemented. -->

# EP052 l5 implementation

Read the [workflow](../../workflows/EP052_l5_workflow.html) and [revised scope](../../lean_delivery/EP052_lean_scope_and_implementation_design.md). Node contracts are in [workflow-data.js](../../workflows/workflow-data.js).

Operate only on assigned gates. Implement the named code/tests, run their acceptance checks and attach observed evidence before changing percentages. Dependencies marked unavailable must remain explicit; a fixture is not a real provider integration.

Agents run outside this system. Do not build an agent scheduler or move participant wallet checks into exchange validation. Minimum investment is one whole unit. Reuse only selected archived code after checking it against these requirements.

Validate the map with `python scripts/validate_workflows.py --phase l5` from the epic root. That helper checks documentation linkage only; it does not execute or certify product gates. Planned application executors must be implemented before runtime acceptance.

This guide corresponds one-to-one with the linked map. It does not grant deployment, credential use or external trades beyond the user's authorised implementation task.

