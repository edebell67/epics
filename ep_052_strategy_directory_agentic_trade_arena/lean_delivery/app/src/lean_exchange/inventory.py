# VERSION HISTORY v1.0.0 · 2026-09-02 · Available-only directory projection over explicit issued units and recorded trades.
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException

from .pricing import PriceError, available_units, latest
from .providers import ProviderError


def router(authority, directory):
    routes, store = APIRouter(), authority.store

    def quote_and_units(db, strategy_id):
        try:
            quote = latest(db, strategy_id)
            return {'price': quote, 'available_units': available_units(db, strategy_id),
                    'issued_units': quote['units_outstanding'], 'valuation_bound': True}
        except PriceError:
            return {'price': None, 'available_units': None, 'issued_units': None, 'valuation_bound': False}

    @routes.get('/v1/strategies')
    def discover(availability: Literal['available', 'all'] = 'available', actor=Depends(authority.authenticate)):
        try:
            source = directory.fetch()
        except ProviderError as exc:
            raise HTTPException(503, str(exc)) from exc
        with store.transaction(immediate=True) as db:
            items = []
            for row in source.items:
                item = row.model_dump(mode='json') | quote_and_units(db, row.strategy_id)
                item['available_to_buy'] = item['valuation_bound'] and item['available_units'] > 0 and row.status == 'active'
                if availability == 'all' or item['available_to_buy']:
                    items.append(item)
        return {'items': items, 'source_version': source.source_version, 'source_total': source.total,
                'inventory_authority': 'explicit_issued_baseline_plus_local_trade_records',
                'notice': 'Unbound prices/units are unknown, never inferred from performance returns.'}

    @routes.get('/v1/strategies/{strategy_id}')
    def detail(strategy_id: str, actor=Depends(authority.authenticate)):
        with store.transaction(immediate=True) as db:
            result = quote_and_units(db, strategy_id)
        if not result['valuation_bound']:
            raise HTTPException(404, 'Strategy valuation not bound')
        return {'strategy_id': strategy_id, **result}

    @routes.get('/v1/strategies/{strategy_id}/price')
    def price(strategy_id: str, actor=Depends(authority.authenticate)):
        try:
            with store.transaction() as db:
                return latest(db, strategy_id)
        except PriceError as exc:
            raise HTTPException(404, str(exc)) from exc

    return routes
