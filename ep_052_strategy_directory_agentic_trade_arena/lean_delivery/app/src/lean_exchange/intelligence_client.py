# VERSION HISTORY v1.0.0 · 2026-09-02 · Replaceable HTTP provider adapter with strict result identity/provenance validation.
import os

import httpx
from pydantic import ValidationError

from .contracts import QueryDelivery, QueryRequest
from .providers import ProviderError


class IntelligenceClient:
    def __init__(self, settings, token=None, transport=None):
        self.settings = settings
        self.token = token or os.environ.get('EP052_INTELLIGENCE_TOKEN')
        self.transport = transport

    def query(self, agent_id: str, request: QueryRequest) -> QueryDelivery:
        if not self.token:
            raise ProviderError('INTELLIGENCE_NOT_CONFIGURED')
        try:
            with httpx.Client(transport=self.transport, timeout=self.settings.provider_timeout_seconds,
                              follow_redirects=False) as client:
                response = client.post(self.settings.intelligence_url,
                                       headers={'Authorization': 'Bearer ' + self.token, 'X-EP052-Agent-ID': agent_id},
                                       json=request.model_dump(mode='json'))
            if response.status_code != 200:
                raise ProviderError('INTELLIGENCE_PROVIDER_FAILED')
            result = QueryDelivery.model_validate(response.json())
            if (result.request_id != request.request_id or result.revision != request.revision
                    or result.query != request or result.mode != self.settings.intelligence_mode
                    or result.created_at.tzinfo is None or not result.source_version
                    or len(result.strategy_ids) > request.limit
                    or len(set(result.strategy_ids)) != len(result.strategy_ids)
                    or (request.strategy_ids and not set(result.strategy_ids) <= set(request.strategy_ids))):
                raise ProviderError('INTELLIGENCE_INVALID_RESULT')
            return result
        except (httpx.HTTPError, ValidationError, ValueError, TypeError) as exc:
            raise ProviderError('INTELLIGENCE_INVALID_OR_UNAVAILABLE') from exc
