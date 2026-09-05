# VERSION HISTORY v1.1.0 · 2026-09-02 · Commit public trade/rejection events with the authoritative settlement outcome.
# v1.0.1 · 2026-09-02 · Validate durable receipts against the published schema and expose it in OpenAPI.
# v1.0.0 · 2026-09-02 · Atomic whole-unit BUY/SELL with participant funding boundary and durable success/rejection retries.
from datetime import datetime, timezone
from decimal import Decimal, localcontext
import json
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from .contracts import TradeRequest, TradeReceipt, fingerprint
from .arena import emit, trade_event
from .participant_funds import FundingError, move
from .pricing import PriceError, available_units, latest, owned_units


class TradeError(ValueError):
    pass


def validate_exchange(request, quote, owned, available, minimum_units):
    """Exchange unit/price requirements only: deliberately no bank, cash or funding dependency."""
    if request.expected_price_version != quote['price_version']:
        raise TradeError('PRICE_CHANGED')
    if request.side == 'BUY':
        if request.units < minimum_units:
            raise TradeError('INVALID_UNITS')
        if request.units > available:
            raise TradeError('SOLD_OUT_OR_INSUFFICIENT_INVENTORY')
    elif request.units > owned:
        raise TradeError('INSUFFICIENT_OWNED_UNITS')


def record_trade(db, receipt, agent_id, request):
    db.execute('INSERT INTO trade_records(id,agent_id,request_id,strategy_id,side,units,price_id,payload) VALUES (?,?,?,?,?,?,?,?)',
               (receipt['trade_id'], agent_id, str(request.request_id), request.strategy_id, request.side,
                request.units, receipt['price_version'], json.dumps(receipt)))


def settle(authority, actor, request):
    store, cfg = authority.store, authority.settings
    request_id, signature = str(request.request_id), fingerprint(request)
    with store.transaction(immediate=True) as db:
        prior = db.execute('SELECT * FROM trade_requests WHERE agent_id=? AND request_id=?', (actor['agent_id'], request_id)).fetchone()
        if prior:
            if prior['fingerprint'] != signature:
                return 409, {'code': 'REQUEST_ID_CONFLICT', 'request_id': request_id}
            return prior['status_code'], json.loads(prior['payload'])
        db.execute('SAVEPOINT trade_effects')
        try:
            quote = latest(db, request.strategy_id)
            own, available = owned_units(db, actor['agent_id'], request.strategy_id), available_units(db, request.strategy_id)
            validate_exchange(request, quote, own, available, cfg.minimum_units)
            if request.side == 'BUY' and own == 0:
                strategies = [row['strategy_id'] for row in db.execute('SELECT DISTINCT strategy_id FROM trade_records WHERE agent_id=?', (actor['agent_id'],))]
                count = sum(owned_units(db, actor['agent_id'], sid) > 0 for sid in strategies)
                if count >= cfg.maximum_positions:
                    raise FundingError('PARTICIPANT_POSITION_LIMIT')
            trade_id = str(uuid4())
            with localcontext() as context:
                context.prec = 60
                gross = Decimal(quote['unit_price']) * request.units
                effect = -gross - cfg.trade_fee if request.side == 'BUY' else gross - cfg.trade_fee
                # Participant function authorises/records funded capacity; exchange validation never sees it.
                funding_reference = move(db, actor['agent_id'], 'trade:' + trade_id, request.side, effect)
            quantity_effect = request.units if request.side == 'BUY' else -request.units
            payload = {'trade_id': trade_id, 'request_id': request_id, 'strategy_id': request.strategy_id,
                       'side': request.side, 'units': request.units, 'status': 'SETTLED',
                       'currency': 'USD', 'unit_price': quote['unit_price'], 'price_version': quote['price_version'],
                       'price_source_version': quote['source_version'], 'price_valued_at': quote['valued_at'],
                       'price_provenance': quote['provenance'], 'gross_amount': str(gross), 'fee': str(cfg.trade_fee),
                       'owned_units_after': own + quantity_effect, 'available_units_before': available,
                       'available_units_after': available - quantity_effect, 'funding_reference': funding_reference,
                       'executed_at': datetime.now(timezone.utc).isoformat()}
            TradeReceipt.model_validate(payload)
            record_trade(db, payload, actor['agent_id'], request)
            trade_event(db, actor['agent_id'], payload)
            status = 200
        except (TradeError, FundingError, PriceError) as exc:
            db.execute('ROLLBACK TO trade_effects')
            status, payload = 409, {'code': str(exc), 'request_id': request_id, 'status': 'REJECTED'}
        db.execute('RELEASE trade_effects')
        if status != 200:
            emit(db, source_key='rejection:' + actor['agent_id'] + ':' + request_id, agent_id=actor['agent_id'],
                 operation='REJECTED', resource_id=request_id, request_id=request_id, strategy_id=request.strategy_id,
                 payload={'side': request.side, 'units': request.units, 'outcome': 'REJECTED'})
        db.execute('INSERT INTO trade_requests VALUES (?,?,?,?,?)', (actor['agent_id'], request_id, signature, status, json.dumps(payload)))
        db.execute('INSERT INTO activity(event_id,occurred_at,owner_id,agent_id,operation,status_code,request_id) VALUES (?,?,?,?,?,?,?)',
                   (str(uuid4()), datetime.now(timezone.utc).isoformat(), actor['owner_id'], actor['agent_id'],
                    'TRADE ' + (request.side if status == 200 else 'REJECTED'), status, request_id))
        return status, payload


def router(authority):
    routes = APIRouter()

    @routes.post('/v1/trades', responses={200: {'model': TradeReceipt}, 409: {'description': 'Recorded rejection or request identity conflict'}})
    def trade(request: TradeRequest, actor=Depends(authority.agent)):
        status, body = settle(authority, actor, request)
        return JSONResponse(body, status_code=status)

    @routes.get('/v1/trades/{trade_id}', responses={200: {'model': TradeReceipt}})
    def get(trade_id: UUID, actor=Depends(authority.agent)):
        with authority.store.transaction() as db:
            row = db.execute('SELECT payload FROM trade_records WHERE id=? AND agent_id=?', (str(trade_id), actor['agent_id'])).fetchone()
            if not row:
                raise HTTPException(404, 'Trade not found')
            return json.loads(row['payload'])

    @routes.get('/v1/me/trades')
    def mine(after: int = Query(default=0, ge=0), actor=Depends(authority.agent)):
        with authority.store.transaction() as db:
            rows = db.execute('SELECT cursor,payload FROM trade_records WHERE agent_id=? AND cursor>? ORDER BY cursor LIMIT ?',
                              (actor['agent_id'], after, authority.settings.activity_page_size)).fetchall()
            return {'items': [json.loads(row['payload']) | {'cursor': row['cursor']} for row in rows],
                    'next_cursor': rows[-1]['cursor'] if rows else after}

    return routes
