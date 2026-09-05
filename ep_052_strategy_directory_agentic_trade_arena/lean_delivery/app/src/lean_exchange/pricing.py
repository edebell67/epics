# VERSION HISTORY v1.0.0 · 2026-09-02 · Publish explicit valuation inputs using the retained NAV/unit formula; never invent live prices.
from datetime import datetime, timezone
import json
from uuid import uuid4

from .providers import ValuationInput, published_price


class PriceError(ValueError):
    pass


def publish(store, settings, valuation: ValuationInput, *, known_strategy_ids: set[str], provenance: str):
    """Operator/provider adapter entry point, not an owner/visiting-agent HTTP endpoint."""
    if valuation.strategy_id not in known_strategy_ids:
        raise PriceError('STRATEGY_NOT_IN_DIRECTORY')
    if not provenance.strip():
        raise PriceError('PRICE_PROVENANCE_REQUIRED')
    if valuation.units_outstanding > 2**63 - 1:
        raise PriceError('ISSUED_UNITS_OUT_OF_RANGE')
    quote = published_price(valuation, settings.price_decimal_places)
    quote['provenance'] = provenance
    with store.transaction(immediate=True) as db:
        old = db.execute('SELECT * FROM price_quotes WHERE strategy_id=? AND source_version=?',
                         (valuation.strategy_id, valuation.source_version)).fetchone()
        if old:
            prior = json.loads(old['payload'])
            if any(prior[key] != value for key, value in quote.items()):
                raise PriceError('PRICE_VERSION_CONFLICT')
            return prior
        latest = db.execute('SELECT payload FROM price_quotes WHERE strategy_id=? ORDER BY sequence DESC LIMIT 1',
                            (valuation.strategy_id,)).fetchone()
        if latest and valuation.valued_at < datetime.fromisoformat(json.loads(latest['payload'])['valued_at']):
            raise PriceError('OUT_OF_ORDER_VALUATION')
        baseline = db.execute('SELECT issued_units FROM strategy_units WHERE strategy_id=?', (valuation.strategy_id,)).fetchone()
        if baseline and baseline['issued_units'] != valuation.units_outstanding:
            raise PriceError('ISSUED_UNIT_BASELINE_CHANGED')
        db.execute('INSERT OR IGNORE INTO strategy_units VALUES (?,?)', (valuation.strategy_id, valuation.units_outstanding))
        quote.update(price_version=str(uuid4()), published_at=datetime.now(timezone.utc).isoformat())
        db.execute('INSERT INTO price_quotes(id,strategy_id,source_version,payload,published_at) VALUES (?,?,?,?,?)',
                   (quote['price_version'], valuation.strategy_id, valuation.source_version, json.dumps(quote), quote['published_at']))
        return quote


def latest(db, strategy_id):
    row = db.execute('SELECT payload FROM price_quotes WHERE strategy_id=? ORDER BY sequence DESC LIMIT 1', (strategy_id,)).fetchone()
    if not row:
        raise PriceError('PRICE_NOT_PUBLISHED')
    return json.loads(row['payload'])


def owned_units(db, agent_id, strategy_id):
    return sum(row['units'] if row['side'] == 'BUY' else -row['units'] for row in db.execute(
        'SELECT side,units FROM trade_records WHERE agent_id=? AND strategy_id=? ORDER BY cursor', (agent_id, strategy_id)))


def available_units(db, strategy_id):
    row = db.execute('SELECT issued_units FROM strategy_units WHERE strategy_id=?', (strategy_id,)).fetchone()
    if not row:
        raise PriceError('INVENTORY_NOT_BOUND')
    allocated = sum(item['units'] if item['side'] == 'BUY' else -item['units'] for item in db.execute(
        'SELECT side,units FROM trade_records WHERE strategy_id=? ORDER BY cursor', (strategy_id,)))
    return row['issued_units'] - allocated
