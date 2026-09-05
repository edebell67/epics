# Test the current EP052 delivery

Version1.1.0 · 2026-09-02 · Primary Arena restored to3D; activity retained as audit tab.
Previous1.0.0 · 2026-09-02. This is access verification, not a declaration of finished MVP delivery.

## One-command access check

In PowerShell:

```powershell
Set-Location 'C:\Users\edebe\eds\epics\ep_052_strategy_directory_agentic_trade_arena\lean_delivery\app'
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python -m lean_exchange.delivery_check
```

Expected result: `http_checks_passed: true`. This checks public discovery, rules, OpenAPI, Arena and owner pages, plus unauthenticated denial on six private routes. No credentials are needed. It submits no trades or paid queries; normal GET activity may be logged.

`published_strategy_count: 0` and `quote_inputs_present: false` currently mean the main exchange has no published valuation inputs. A passing access check does **not** make those strategies tradable. `full_mvp_acceptance` deliberately remains `NOT_ASSESSED`, even when prices exist.

To retain a sanitized result, add `--output` followed by a new JSON filename. An existing file is never overwritten. To inspect the isolated worked-case service, add `--base-url http://127.0.0.1:8056`; its prices are acceptance fixtures, not the main directory's current valuations.

## Open the delivered interfaces

The Arena now opens with the3D trading floor. Drag or use arrow keys to orbit, use zoom controls, and select a booth through its label or the accessible booth list. Search/page the directory, or select **Available to buy only**. All-directory mode explicitly labels unpriced/sold-out booths; it is not a purchase selector. The inspector shows current API values and provenance. **Activity audit** retains the detailed event/filter view. Camera controls never start or pause agents. No figures appear when no agents are currently connected; historical disconnects remain in the activity feed. Prices and fee amounts are not synthesised by the visual layer.

Refresh an already open Arena tab to load the new assets. The existing review credential remains valid on8056. Its one priced strategy still uses explicit acceptance-fixture valuation, not an invented live directory price. The hosted reference site was not changed.

- [Main API explorer](http://127.0.0.1:8054/docs)
- [Main Arena](http://127.0.0.1:8054/arena)
- [Main owner workspace](http://127.0.0.1:8054/owner)
- [Common visitor rules](http://127.0.0.1:8054/v1/rules/agent_rules)
- [Workflow and gate evidence](http://127.0.0.1:8053/EP052_lean_implementation_workflow.html)
- [Isolated worked-case owner view](http://127.0.0.1:8056/owner)

Private operations need the appropriate existing owner or agent credential. Do not paste credentials into chat, URLs or shared evidence. Use the API explorer's Authorize control or the workspace's credential field. An owner token is not a visiting-agent token. The access checker intentionally does not create identities or prove authenticated owner isolation; separate scope tests cover that.

If the local API is stopped, the existing `scripts/start_lean_api.ps1` starts the main exchange and separate simulated intelligence service without restarting occupied ports. It does not start agents, publish prices, or launch the isolated review automatically. Diagnose an occupied/unhealthy port rather than starting a second authority.

## Remaining acceptance work

Actual valuation binding, updated-process recovery/activity verification, exact375px browser acceptance and the real Hermes one/ten-agent demonstrations remain open. WSL Hermes currently needs reauthentication. See the workflow for current status; test counts and HTTP200 alone do not close these gates.
