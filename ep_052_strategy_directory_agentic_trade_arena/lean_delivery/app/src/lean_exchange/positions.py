# VERSION HISTORY v1.0.0 · 2026-09-02 · Owner-scoped position snapshots and record-linked value attribution without lot-policy or price invention.
from datetime import datetime, timezone
from decimal import Decimal, localcontext
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query


def instant(value):
    return datetime.fromisoformat(value) if isinstance(value, str) else value


def history(db, agent_id):
    return [json.loads(row['payload']) for row in db.execute(
        'SELECT payload FROM trade_records WHERE agent_id=? ORDER BY cursor', (agent_id,))]


def quote_at(db, strategy_id, at):
    # Published time, not the source's potentially backdated valuation time, controls visibility.
    for row in db.execute('SELECT payload FROM price_quotes WHERE strategy_id=? ORDER BY sequence DESC', (strategy_id,)):
        quote = json.loads(row['payload'])
        if instant(quote['published_at']) <= at:
            return quote
    return None


def snapshot(db, agent_id, at):
    allocation = db.execute('SELECT * FROM participant_allocations WHERE agent_id=?', (agent_id,)).fetchone()
    if not allocation or instant(allocation['created_at']) > at:
        raise HTTPException(422, 'SNAPSHOT_PRECEDES_PARTICIPANT_ALLOCATION')
    all_trades = history(db, agent_id)
    trades = [trade for trade in all_trades if instant(trade['executed_at']) <= at]
    trade_times = {'trade:' + trade['trade_id']: instant(trade['executed_at']) for trade in all_trades}
    movements = [dict(row) for row in db.execute(
        'SELECT * FROM participant_movements WHERE agent_id=? ORDER BY created_at,id', (agent_id,))
        if trade_times.get(row['operation_id'], instant(row['created_at'])) <= at]
    positions = []
    with localcontext() as context:
        context.prec = 60
        cash = Decimal(allocation['seed_usd']) + sum((Decimal(row['amount_usd']) for row in movements), Decimal(0))
        trade_fees = sum((Decimal(trade['fee']) for trade in trades), Decimal(0))
        query_fees = -sum((Decimal(row['amount_usd']) for row in movements if row['kind'] == 'INTELLIGENCE'), Decimal(0))
        total = Decimal(0)
        complete = True
        for sid in sorted({trade['strategy_id'] for trade in trades}):
            related = [trade for trade in trades if trade['strategy_id'] == sid]
            units = sum(trade['units'] * (1 if trade['side'] == 'BUY' else -1) for trade in related)
            if units == 0:
                continue
            quote = quote_at(db, sid, at)
            marked = Decimal(quote['unit_price']) * units if quote else None
            complete = complete and marked is not None
            if marked is not None:
                total += marked
            positions.append({'strategy_id': sid, 'units': units, 'price': quote,
                              'marked_value_usd': str(marked) if marked is not None else None,
                              'entry_trades': [trade for trade in related if trade['side'] == 'BUY'],
                              'trade_ids': [trade['trade_id'] for trade in related],
                              'entry_note': 'Original entries retained; no allocation of sold units to entry lots is implied.'})
        return {'agent_id': agent_id, 'as_of': at.isoformat(), 'currency': 'USD',
                'seed_usd': allocation['seed_usd'], 'allocation_created_at': allocation['created_at'], 'spendable_usd': str(cash),
                'positions': positions, 'valuation_complete': complete,
                'holdings_value_usd': str(total) if complete else None,
                'total_value_usd': str(cash + total) if complete else None,
                'gain_since_seed_usd': str(cash + total - Decimal(allocation['seed_usd'])) if complete else None,
                'trade_fees_usd': str(trade_fees), 'intelligence_fees_usd': str(query_fees),
                'unrealised_gains_spendable': False}


def attribute(db, agent_id, start, end):
    opening, closing = snapshot(db, agent_id, start), snapshot(db, agent_id, end)
    trades = [trade for trade in history(db, agent_id) if start < instant(trade['executed_at']) <= end]
    opening_units = {row['strategy_id']: row['units'] for row in opening['positions']}
    closing_units = {row['strategy_id']: row['units'] for row in closing['positions']}
    lines = []
    complete = opening['valuation_complete'] and closing['valuation_complete']
    with localcontext() as context:
        context.prec = 60
        market_total = Decimal(0)
        for sid in sorted(set(opening_units) | set(closing_units) | {trade['strategy_id'] for trade in trades}):
            first, last = quote_at(db, sid, start), quote_at(db, sid, end)
            related = [trade for trade in trades if trade['strategy_id'] == sid]
            units = opening_units.get(sid, 0)
            known = last is not None and (first is not None or units == 0)
            complete = complete and known
            opening_effect = Decimal(units) * (Decimal(last['unit_price']) - Decimal(first['unit_price'])) if known and units else Decimal(0)
            trade_effects = [{'trade_id': trade['trade_id'], 'side': trade['side'], 'units': trade['units'],
                             'execution_price_usd': trade['unit_price'], 'fee_usd': trade['fee'],
                             'price_version': trade['price_version'],
                             'value_change_usd': str((1 if trade['side'] == 'BUY' else -1) * trade['units'] *
                                                    (Decimal(last['unit_price']) - Decimal(trade['unit_price']))) if known else None}
                            for trade in related]
            effect = opening_effect + sum((Decimal(item['value_change_usd']) for item in trade_effects), Decimal(0)) if known else None
            if effect is not None:
                market_total += effect
            lines.append({'strategy_id': sid, 'opening_units': units, 'closing_units': closing_units.get(sid, 0),
                          'opening_price': first, 'closing_price': last,
                          'opening_units_price_change_usd': str(opening_effect) if known else None,
                          'trade_effects': trade_effects, 'price_and_trade_gain_usd': str(effect) if known else None})
        trade_fees = Decimal(closing['trade_fees_usd']) - Decimal(opening['trade_fees_usd'])
        query_fees = Decimal(closing['intelligence_fees_usd']) - Decimal(opening['intelligence_fees_usd'])
        charges = [dict(row) for row in db.execute(
            "SELECT id,operation_id,amount_usd,created_at FROM participant_movements WHERE agent_id=? AND kind='INTELLIGENCE' ORDER BY created_at,id", (agent_id,))
            if start < instant(row['created_at']) <= end]
        observed = Decimal(closing['total_value_usd']) - Decimal(opening['total_value_usd']) if complete else None
        explained = market_total - trade_fees - query_fees if complete else None
        return {'agent_id': agent_id, 'from': start.isoformat(), 'to': end.isoformat(), 'currency': 'USD',
                'opening': opening, 'closing': closing, 'strategies': lines, 'query_charges': charges,
                'trade_fees_usd': str(trade_fees), 'intelligence_fees_usd': str(query_fees),
                'price_and_trade_gain_usd': str(market_total) if complete else None,
                'cash_change_usd': str(Decimal(closing['spendable_usd']) - Decimal(opening['spendable_usd'])),
                'value_change_usd': str(observed) if complete else None,
                'explained_change_usd': str(explained) if complete else None,
                'reconciliation_difference_usd': str(observed - explained) if complete else None,
                'reconciled': complete and observed == explained,
                'formula': 'Opening units × price change + signed traded units × (closing price − execution price) − trade fees − query fees.'}


def router(authority):
    routes = APIRouter()

    def owned(db, owner_id, agent_id):
        row = db.execute('SELECT id FROM agents WHERE id=? AND owner_id=?', (agent_id, owner_id)).fetchone()
        if not row:
            raise HTTPException(404, 'Agent not found')

    @routes.get('/v1/me/positions')
    def mine(actor=Depends(authority.agent)):
        with authority.store.transaction(immediate=True) as db:
            return snapshot(db, actor['agent_id'], datetime.now(timezone.utc))

    @routes.get('/v1/owner/positions')
    def group(agent_id: list[UUID] | None = Query(default=None), actor=Depends(authority.owner)):
        with authority.store.transaction(immediate=True) as db:
            ids = list(dict.fromkeys(str(item) for item in agent_id)) if agent_id else [
                row['id'] for row in db.execute('SELECT id FROM agents WHERE owner_id=? ORDER BY id', (actor['owner_id'],))]
            for aid in ids:
                owned(db, actor['owner_id'], aid)
            now = datetime.now(timezone.utc)
            agents = [snapshot(db, aid, now) for aid in ids]
            complete = all(agent['valuation_complete'] for agent in agents)
            with localcontext() as context:
                context.prec = 60
                totals = {key: str(sum((Decimal(agent[key]) for agent in agents), Decimal(0)))
                          if key not in ('holdings_value_usd', 'total_value_usd', 'gain_since_seed_usd') or complete else None
                          for key in ('seed_usd', 'spendable_usd', 'holdings_value_usd', 'total_value_usd', 'gain_since_seed_usd',
                                      'trade_fees_usd', 'intelligence_fees_usd')}
            return {'as_of': now.isoformat(), 'currency': 'USD', 'agents': agents, 'agent_count': len(agents),
                    'valuation_complete': complete, 'totals': totals}

    @routes.get('/v1/owner/agents/{agent_id}/value-change')
    def change(agent_id: UUID, start: datetime = Query(alias='from'), end: datetime = Query(alias='to'),
               actor=Depends(authority.owner)):
        if start.tzinfo is None or end.tzinfo is None or start > end or end > datetime.now(timezone.utc):
            raise HTTPException(422, 'Use timezone-aware from <= to <= now')
        with authority.store.transaction(immediate=True) as db:
            owned(db, actor['owner_id'], str(agent_id))
            return attribute(db, str(agent_id), start, end)

    return routes
