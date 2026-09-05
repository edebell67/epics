# VERSION HISTORY v1.0.0 · 2026-09-02 · Durable shared research/trade/presence projections with allowlisted payloads and resumable filtering.
from datetime import datetime, timezone
import json
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query


def emit(db, *, source_key, agent_id, operation, resource_id, payload, request_id=None, strategy_id=None, occurred_at=None):
    occurred_at = (datetime.fromisoformat(occurred_at) if occurred_at else datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat(timespec='microseconds')
    db.execute('INSERT OR IGNORE INTO arena_events(event_id,source_key,occurred_at,agent_id,operation,strategy_id,resource_id,request_id,payload) VALUES (?,?,?,?,?,?,?,?,?)',
               (str(uuid4()), source_key, occurred_at, agent_id, operation,
                strategy_id, resource_id, request_id, json.dumps(payload)))


def trade_event(db, agent_id, trade):
    public = {key: trade[key] for key in ('side', 'units', 'unit_price', 'currency', 'fee', 'price_version',
                                        'price_provenance', 'available_units_before', 'available_units_after')}
    emit(db, source_key='trade:' + trade['trade_id'], agent_id=agent_id, operation=trade['side'],
         strategy_id=trade['strategy_id'], resource_id=trade['trade_id'], request_id=trade['request_id'],
         payload=public, occurred_at=trade['executed_at'])


def query_event(db, agent_id, delivery, fee, occurred_at=None):
    query = delivery['query']
    # The free-form kind may contain participant-private text; expose recognised research categories only.
    allowed = {'random', 'top_strategy', 'lowest_drawdown', 'regime_similarity', 'fastest_improving', 'best_performance'}
    public = {'kind': query['kind'] if query['kind'] in allowed else 'custom',
              'window_start': query.get('window_start'), 'window_end': query.get('window_end'),
              'strategy_ids': delivery['strategy_ids'], 'result_count': len(delivery['strategy_ids']),
              'mode': delivery['mode'], 'result_version': str(delivery['result_version']), 'fee_usd': str(fee)}
    emit(db, source_key='query:' + str(delivery['delivery_id']), agent_id=agent_id, operation='QUERY',
         resource_id=str(delivery['delivery_id']), request_id=str(delivery['request_id']), payload=public,
         occurred_at=occurred_at)


def report_event(db, agent_id, report_id, request_id, action, trade_id, occurred_at):
    emit(db, source_key='report:' + report_id, agent_id=agent_id, operation='REPORT', resource_id=report_id,
         request_id=request_id, occurred_at=occurred_at, payload={'action': action, 'trade_id': trade_id})


def backfill(db):
    if db.execute("SELECT 1 FROM metadata WHERE key='arena_backfill_v1'").fetchone():
        return
    for row in db.execute('SELECT agent_id,payload FROM trade_records ORDER BY cursor').fetchall():
        trade_event(db, row['agent_id'], json.loads(row['payload']))
    for row in db.execute('SELECT * FROM query_deliveries').fetchall():
        movement = db.execute('SELECT created_at FROM participant_movements WHERE agent_id=? AND operation_id=?',
                              (row['agent_id'], 'query:' + row['id'])).fetchone()
        delivery = json.loads(row['payload'])
        query_event(db, row['agent_id'], delivery, row['fee_usd'], movement['created_at'] if movement else delivery['created_at'])
    for row in db.execute('SELECT * FROM decision_reports ORDER BY cursor').fetchall():
        report = json.loads(row['payload'])
        report_event(db, row['agent_id'], row['id'], row['request_id'], report['action'], report.get('trade_id'), row['created_at'])
    for row in db.execute("SELECT agent_id,request_id,min(occurred_at) AS occurred_at FROM activity WHERE operation='TRADE REJECTED' AND agent_id IS NOT NULL AND request_id IS NOT NULL GROUP BY agent_id,request_id").fetchall():
        emit(db, source_key='rejection:' + row['agent_id'] + ':' + row['request_id'], agent_id=row['agent_id'],
             operation='REJECTED', resource_id=row['request_id'], request_id=row['request_id'], occurred_at=row['occurred_at'],
             payload={'outcome': 'REJECTED', 'notice': 'Historical rejection; strategy and units were not retained in the earlier action record.'})
    db.execute("INSERT INTO metadata VALUES ('arena_backfill_v1','complete')")


def router(authority):
    routes = APIRouter()

    def read(after, limit, agent_id, strategy_id, operation, start, end):
        limit = limit or authority.settings.activity_page_size
        if limit > authority.settings.activity_page_size:
            raise HTTPException(422, 'Configured activity page limit exceeded')
        if any(value is not None and value.tzinfo is None for value in (start, end)) or (start and end and start > end):
            raise HTTPException(422, 'Use timezone-aware from <= to')
        clauses, params = ['cursor>?'], [after]
        for column, value in [('agent_id', agent_id), ('operation', operation)]:
            if value is not None:
                clauses.append(column + '=?'); params.append(str(value))
        if strategy_id is not None:
            clauses.append("(strategy_id=? OR (operation='QUERY' AND EXISTS (SELECT 1 FROM json_each(arena_events.payload,'$.strategy_ids') WHERE value=?)))")
            params.extend([strategy_id, strategy_id])
        # UTC microsecond strings preserve precise interval boundaries without SQLite date rounding.
        for comparator, value in [('>=', start), ('<=', end)]:
            if value:
                clauses.append('occurred_at' + comparator + '?'); params.append(value.astimezone(timezone.utc).isoformat(timespec='microseconds'))
        with authority.store.transaction(immediate=True) as db:
            high_water = db.execute('SELECT coalesce(max(cursor),0) FROM arena_events').fetchone()[0]
            rows = db.execute('SELECT * FROM arena_events WHERE ' + ' AND '.join(clauses) + ' ORDER BY cursor LIMIT ?', (*params, limit + 1)).fetchall()
            more = len(rows) > limit
            rows = rows[:limit]
            items = [{key: row[key] for key in ('cursor','event_id','occurred_at','agent_id','operation','strategy_id','resource_id','request_id')} |
                     {'details': json.loads(row['payload'])} for row in rows]
        return {'items': items, 'next_cursor': rows[-1]['cursor'] if more else max(after, high_water),
                'has_more': more, 'high_water_cursor': high_water,
                'notice': 'Shared activity excludes private funding, feedback, explanations and unrecognised free-form research text. Change filters with cursor0.'}

    @routes.get('/v1/arena/activity')
    def events(after: int = Query(default=0, ge=0), limit: int | None = Query(default=None, gt=0),
               agent_id: UUID | None = None, strategy_id: str | None = Query(default=None, pattern=r'^DNA_[0-9]+$'),
               operation: Literal['BUY','SELL','QUERY','REPORT','REJECTED','CONNECT','DISCONNECT'] | None = None,
               start: datetime | None = Query(default=None, alias='from'), end: datetime | None = Query(default=None, alias='to'),
               actor=Depends(authority.authenticate)):
        return read(after, limit, agent_id, strategy_id, operation, start, end)

    @routes.get('/v1/arena/inventory-effects')
    def effects(after: int = Query(default=0, ge=0), limit: int | None = Query(default=None, gt=0),
                actor=Depends(authority.authenticate)):
        # The canonical feed carries the same trade identity; callers advance over non-trade events safely.
        page = read(after, limit, None, None, None, None, None)
        page['items'] = [item for item in page['items'] if item['operation'] in ('BUY','SELL')]
        return page

    return routes
