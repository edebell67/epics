# Example individual trading skill — version 1.0

Owner-configurable example; not an exchange-wide trading policy and not an executed agent.

## Individual settings

- polling_interval_minutes: 5 (example default; owner changes independently per agent).
- buy_units: 1 (example default; owner-configurable, within common rules and funded allocation).
- take_profit_percent: 10 (example default; owner-configurable).
- selection: first strategy by position value returned by the intelligence layer.

## Behaviour

At your own configured interval, read your positions, owner feedback, available inventory, published prices and active common rules. Decide BUY, SELL or HOLD independently.

For a new entry, request the relevant intelligence and choose its #1 available candidate according to this skill. During simulated_random mode, the first result is a random test candidate, NOT a genuine #1 analytical ranking. Disclose this in your action explanation.

Buy the configured number of whole units only if permitted and funded. Preserve the confirmed entry price. This simple example does not add to a strategy already held, so its entry-price trigger is unambiguous.

Sell the held position when its published price is at least entry_price × (1 + take_profit_percent / 100). Otherwise HOLD or choose another permitted entry according to this skill. A price increase is not spendable cash until sold.

Use only authenticated APIs; inspect the actual result and record/acknowledge activity as supported. Do not ask the exchange to run this loop.
