# VERSION HISTORY v1.0.1 · 2026-09-02 · Read participant funds and movements from one consistent snapshot during concurrent settlement.
# v1.0.0 · 2026-09-02 · Participant-owned seed and Decimal movements; no exchange wallet reader or public credit API.
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException


class FundingError(ValueError):
    pass


def initialise(db, agent_id: str, seed: Decimal):
    if not seed.is_finite() or seed < 0:
        raise FundingError('INVALID_SEED')
    db.execute('INSERT OR IGNORE INTO participant_allocations VALUES (?,?,?)',
               (agent_id, str(seed), datetime.now(timezone.utc).isoformat()))


def balance(db, agent_id: str) -> Decimal:
    allocation = db.execute('SELECT seed_usd FROM participant_allocations WHERE agent_id=?', (agent_id,)).fetchone()
    if not allocation:
        raise FundingError('ALLOCATION_NOT_FOUND')
    with localcontext() as context:
        context.prec = 50
        return Decimal(allocation['seed_usd']) + sum((Decimal(row['amount_usd']) for row in db.execute(
            'SELECT amount_usd FROM participant_movements WHERE agent_id=?', (agent_id,))), Decimal(0))


def move(db, agent_id: str, operation_id: str, kind: str, amount: Decimal):
    """Caller holds an IMMEDIATE transaction; effects roll back with the recorded operation."""
    if not amount.is_finite():
        raise FundingError('INVALID_AMOUNT')
    if kind not in ('BUY', 'SELL', 'INTELLIGENCE'):
        raise FundingError('INVALID_MOVEMENT_KIND')
    if kind in ('BUY', 'INTELLIGENCE') and amount > 0:
        raise FundingError('INVALID_DEBIT')
    row = db.execute('SELECT * FROM participant_movements WHERE agent_id=? AND operation_id=?',
                     (agent_id, operation_id)).fetchone()
    if row:
        if row['kind'] != kind or Decimal(row['amount_usd']) != amount:
            raise FundingError('FUNDING_REFERENCE_CONFLICT')
        return row['id']
    if balance(db, agent_id) + amount < 0:
        raise FundingError('PARTICIPANT_FUNDS_INSUFFICIENT')
    movement_id = str(uuid4())
    db.execute('INSERT INTO participant_movements VALUES (?,?,?,?,?,?)',
               (movement_id, agent_id, operation_id, kind, str(amount), datetime.now(timezone.utc).isoformat()))
    return movement_id


def router(authority):
    routes = APIRouter()

    def view(agent_id):
        with authority.store.transaction(immediate=True) as db:
            allocation = db.execute('SELECT * FROM participant_allocations WHERE agent_id=?', (agent_id,)).fetchone()
            if not allocation:
                raise HTTPException(404, 'Participant allocation not found')
            movements = [dict(row) for row in db.execute('SELECT * FROM participant_movements WHERE agent_id=? ORDER BY created_at,id', (agent_id,))]
            return {'agent_id': agent_id, 'currency': 'USD', 'seed_usd': allocation['seed_usd'],
                    'spendable_usd': str(balance(db, agent_id)), 'movements': movements,
                    'boundary': 'participant', 'unrealised_gains_spendable': False}

    @routes.get('/participant/v1/me/funds')
    def mine(actor=Depends(authority.agent)):
        return view(actor['agent_id'])

    @routes.get('/participant/v1/owner/agents/{agent_id}/funds')
    def owned(agent_id: UUID, actor=Depends(authority.owner)):
        with authority.store.transaction() as db:
            row = db.execute('SELECT id FROM agents WHERE id=? AND owner_id=?', (str(agent_id), actor['owner_id'])).fetchone()
            if not row:
                raise HTTPException(404, 'Agent not found')
        return view(str(agent_id))

    return routes
