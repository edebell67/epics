# VERSION HISTORY v1.11.0 · 2026-09-05 · Read allowed hosts from EP052_ALLOWED_HOSTS so hosted deploys aren't rejected by TrustedHostMiddleware.
# v1.10.0 · 2026-09-02 · Advertise the read-only live Arena workspace.
# v1.9.0 · 2026-09-02 · Serve authenticated shared Arena projections with resumable filtering.
# v1.8.0 · 2026-09-02 · Expose private positions and owner value-change reconciliation from recorded prices/trades.
# v1.7.2 · 2026-09-02 · Advertise verified trade-report links and updated visitor rules after live settlement verification.
# v1.7.1 · 2026-09-02 · Expose non-secret instance identity and bound-quote count for review/sync provenance.
# v1.7.0 · 2026-09-02 · Mount recorded trades and priced inventory; missing valuation inputs fail closed.
# v1.6.1 · 2026-09-02 · Publish feedback/HOLD rule revision.
# v1.6.0 · 2026-09-02 · Serve API-driven owner feedback workspace, with no simulated agent controls.
# v1.5.0 · 2026-09-02 · Expose private feedback/replies and external HOLD reports; trade linking remains unavailable.
# v1.4.1 · 2026-09-02 · Advertise funded-query visitor rule revision.
# v1.4.0 · 2026-09-02 · Participant allocations and paid intelligence delivery with durable recovery.
# v1.3.1 · 2026-09-02 · Advertise updated visiting-rule version for live connection instructions.
# v1.3.0 · 2026-09-02 · Mount durable owner/agent authentication, independent connections and safe activity access.
# v1.2.0 · 2026-09-02 · Publish executable contract schemas and validation-only routes for review.
# v1.1.0 · 2026-09-02 · Expose read-only source diagnostics without claiming tradable inventory or prices.
# v1.0.0 · 2026-09-02 · Live discovery/configuration/rule delivery; only implemented capabilities advertised.
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .config import APP_ROOT, Settings, load_settings
from .providers import DirectoryProvider, DirectorySnapshot, ProviderError
from .contracts import TradeRequest, QueryRequest, schema_catalogue, fingerprint
from .intelligence import contract
from .records import Store
from .auth import Authority
from . import access, activity, connections, participant_funds, query_gateway, feedback, decisions, views, inventory, trades, positions, arena
from .intelligence_client import IntelligenceClient
import time

RULES_ROOT = APP_ROOT.parents[1] / 'rules'


def create_app(settings: Settings | None = None, rules_root: Path | None = None,
               directory: DirectoryProvider | None = None, database: Path | None = None, clock=time.time,
               intelligence_provider=None) -> FastAPI:
    cfg = settings or load_settings()
    root = rules_root or RULES_ROOT
    provider = directory or DirectoryProvider(cfg)
    authority = Authority(Store(database), cfg, clock)
    with authority.store.transaction() as db:
        for row in db.execute('SELECT id FROM agents').fetchall():
            participant_funds.initialise(db, row['id'], cfg.seed_funds)
    app = FastAPI(title='EP052 Lean Exchange API', version='0.1.0',
                  description='Visiting-agent API. Only listed endpoints are implemented; no agent runner.')
    default_hosts = '127.0.0.1,localhost,testserver'
    allowed_hosts = [h.strip() for h in os.environ.get('EP052_ALLOWED_HOSTS', default_hosts).split(',') if h.strip()]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)
    app.add_middleware(activity.ActionMiddleware, authority=authority)
    app.state.authority = authority
    app.include_router(access.router(authority))
    app.include_router(connections.router(authority))
    app.include_router(activity.router(authority))
    app.include_router(participant_funds.router(authority))
    app.include_router(query_gateway.router(authority, intelligence_provider or IntelligenceClient(cfg)))
    app.include_router(feedback.router(authority))
    app.include_router(decisions.router(authority))
    app.include_router(views.router())
    app.include_router(inventory.router(authority, provider))
    app.include_router(trades.router(authority))
    app.include_router(positions.router(authority))
    app.include_router(arena.router(authority))

    @app.get('/health')
    def health():
        return {'status': 'ok', 'environment': cfg.environment, 'service': 'ep052-lean-exchange'}

    @app.get('/v1/exchange')
    def exchange():
        with authority.store.transaction() as db:
            instance_id = db.execute("SELECT value FROM metadata WHERE key='instance_id'").fetchone()['value']
            published_count = db.execute('SELECT count(*) FROM strategy_units').fetchone()[0]
        return {
            'instance_id': instance_id,
            'published_strategy_count': published_count,
            'environment': cfg.environment,
            'rules_version': '1.6',
            'configuration': cfg.model_dump(mode='json'),
            'capabilities': ['discovery', 'rules', 'directory_source_inspection', 'contract_validation',
                             'owner_agent_credentials', 'connections', 'scoped_activity',
                             'participant_funds', 'intelligence_gateway', 'feedback_api', 'hold_reports', 'feedback_view',
                             'trade_recording', 'priced_inventory', 'verified_trade_reports', 'positions', 'value_attribution', 'arena_activity_api', 'arena_activity_view'],
            'not_yet_available': [],
            'arena_view': '/arena',
            'trade_readiness': 'Requires explicit operator-published valuation and issued-unit inputs; no default prices invented.',
            'participant_funds': '/participant/v1/me/funds',
            'intelligence_queries': '/participant/v1/me/queries',
            'rules': ['/v1/rules/exchange_rules', '/v1/rules/agent_rules', '/v1/rules/example_trading_skill'],
            'openapi': '/openapi.json',
            'directory_source': '/v1/providers/directory',
            'contracts': '/v1/contracts',
        }

    @app.get('/v1/providers/directory', response_model=DirectorySnapshot)
    def directory_source():
        """Inspect the existing public source. This is not an available-to-buy endpoint."""
        try:
            return provider.fetch()
        except ProviderError as exc:
            raise HTTPException(503, detail={'code': str(exc), 'retryable': True}) from exc

    @app.get('/v1/contracts')
    def contracts():
        return {'schemas': schema_catalogue(), 'validation_only': True,
                'note': 'Contract validation does not connect, trade, query or charge an agent.',
                'intelligence': '/v1/contracts/intelligence'}

    @app.get('/v1/contracts/intelligence')
    def intelligence_contract():
        return contract(cfg)

    @app.post('/v1/contracts/validate/trade')
    def validate_trade(request: TradeRequest):
        if request.units < cfg.minimum_units:
            raise HTTPException(422, detail={'code': 'INVALID_UNITS', 'minimum_units': cfg.minimum_units})
        return {'valid': True, 'executed': False, 'fingerprint': fingerprint(request)}

    @app.post('/v1/contracts/validate/query')
    def validate_query(request: QueryRequest):
        if request.limit > cfg.max_query_results:
            raise HTTPException(422, detail={'code': 'QUERY_LIMIT', 'maximum': cfg.max_query_results})
        return {'valid': True, 'delivered': False, 'charged': False, 'fingerprint': fingerprint(request)}

    @app.get('/v1/rules/{name}', response_class=PlainTextResponse)
    def rules(name: str):
        allowed = {'exchange_rules': 'exchange_rules.md', 'agent_rules': 'agent_rules.md',
                   'example_trading_skill': 'agents/example/trading_skill.md'}
        if name not in allowed:
            raise HTTPException(404, 'Unknown rule document')
        return root.joinpath(allowed[name]).read_text(encoding='utf-8')

    return app
