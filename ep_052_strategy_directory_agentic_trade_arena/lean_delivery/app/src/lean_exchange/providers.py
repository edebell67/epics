# VERSION HISTORY v1.0.0 · 2026-09-02 · Read-only directory adapter with strict pagination and honest price provenance.
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from hashlib import sha256
import json
from typing import Any, Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from .config import Settings


class ProviderError(Exception):
    """Safe error: never include upstream body, URL credentials or request headers."""


class StrategyRecord(BaseModel):
    model_config = ConfigDict(extra='allow', allow_inf_nan=False)
    strategy_id: str = Field(pattern=r'^DNA_[0-9]+$')
    status: str
    descriptive_name: str | None = None
    total_trades: int = Field(ge=0, strict=True)
    total_net_return: Decimal
    open_trades: int | None = Field(default=None, ge=0, strict=True)
    open_net_return: Decimal | None = None


class DirectorySnapshot(BaseModel):
    items: list[StrategyRecord]
    source: Literal['existing_strategy_directory'] = 'existing_strategy_directory'
    source_version: str
    retrieved_at: datetime
    page_as_of: list[datetime]
    total: int
    open_evidence_available: bool
    exchange_prices_available: Literal[False] = False
    warnings: list[str]


class DirectoryProvider:
    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None):
        self.settings = settings
        self.transport = transport

    def fetch(self) -> DirectorySnapshot:
        cfg = self.settings
        items: list[StrategyRecord] = []
        timestamps: list[datetime] = []
        expected_total = None
        identifiers: set[str] = set()
        try:
            with httpx.Client(timeout=cfg.provider_timeout_seconds, transport=self.transport,
                              follow_redirects=False) as client:
                for page in range(1, cfg.directory_max_pages + 1):
                    response = client.get(cfg.directory_url, params={'page': page, 'page_size': cfg.directory_page_size})
                    if response.status_code != 200:
                        raise ProviderError('DIRECTORY_UNAVAILABLE')
                    payload = response.json()
                    data = payload['data']
                    total = data['total']
                    if type(total) is not int or total < 0 or data['page'] != page:
                        raise ProviderError('DIRECTORY_INVALID_PAGINATION')
                    if expected_total is None:
                        expected_total = total
                    if total != expected_total:
                        raise ProviderError('DIRECTORY_CHANGED_DURING_READ')
                    stamp = datetime.fromisoformat(payload['as_of'])
                    if stamp.tzinfo is None:
                        raise ProviderError('DIRECTORY_MISSING_TIMEZONE')
                    timestamps.append(stamp)
                    batch = [StrategyRecord.model_validate(row) for row in data['items']]
                    for record in batch:
                        if record.strategy_id in identifiers:
                            raise ProviderError('DIRECTORY_DUPLICATE_STRATEGY')
                        identifiers.add(record.strategy_id)
                    items.extend(batch)
                    if len(items) > total or len(batch) > cfg.directory_page_size:
                        raise ProviderError('DIRECTORY_INVALID_PAGINATION')
                    if len(items) == total:
                        break
                    if not batch:
                        raise ProviderError('DIRECTORY_INCOMPLETE')
                else:
                    raise ProviderError('DIRECTORY_PAGE_LIMIT')
        except (httpx.HTTPError, ValidationError, ValueError, KeyError, TypeError) as exc:
            raise ProviderError('DIRECTORY_INVALID_OR_UNAVAILABLE') from exc
        canonical = [item.model_dump(mode='json') for item in sorted(items, key=lambda x: x.strategy_id)]
        version = sha256(json.dumps(canonical, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        open_available = bool(items) and all(x.open_trades is not None and x.open_net_return is not None for x in items)
        return DirectorySnapshot(items=items, total=len(items), source_version=version,
                                 retrieved_at=datetime.now(timezone.utc), page_as_of=timestamps,
                                 open_evidence_available=open_available,
                                 warnings=['Catalogue/performance is not published USD unit pricing.'] +
                                 ([] if open_available else ['Source omits open-position evidence; unknown is not zero.']))


class ValuationInput(BaseModel):
    """Adapted NAV/unit invariant from archived core.models.StrategyValuation; DNA IDs retained."""
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    strategy_id: str = Field(pattern=r'^DNA_[0-9]+$')
    nav: Decimal = Field(ge=0, max_digits=28, decimal_places=10)
    units_outstanding: int = Field(gt=0, strict=True)
    currency: Literal['USD']
    source_version: str = Field(min_length=1, max_length=128)
    valued_at: datetime

    @field_validator('valued_at')
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError('Valuation time requires timezone')
        return value


def published_price(valuation: ValuationInput, decimal_places: int) -> dict[str, Any]:
    if type(decimal_places) is not int or not 0 <= decimal_places <= 18:
        raise ValueError('Unsupported price precision')
    with localcontext() as context:
        context.prec = 50
        price = (valuation.nav / valuation.units_outstanding).quantize(Decimal(1).scaleb(-decimal_places))
    return valuation.model_dump(mode='json') | {'unit_price': str(price), 'method': 'NAV / units_outstanding'}
