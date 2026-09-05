# VERSION HISTORY v1.1.1 · 2026-09-02 · Declare scoped owner/status fields returned by actual activity records.
# v1.1.0 · 2026-09-02 · Align settlement receipt schema with persisted price provenance and funding references.
# v1.0.1 · 2026-09-02 · Reject units beyond the persistent integer representation before settlement.
# v1.0.0 · 2026-09-02 · Executable visitor schemas and explicit non-executing contract validation.
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
import json
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

StrategyId = Annotated[str, Field(pattern=r'^DNA_[0-9]+$')]
WholeUnits = Annotated[int, Field(strict=True, gt=0, le=2**63-1)]
SafeText = Annotated[str, Field(min_length=1, max_length=2000)]


class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class ConnectionRequest(Contract):
    request_id: UUID
    purpose: Literal['strategy_trading']


class TradeRequest(Contract):
    request_id: UUID
    strategy_id: StrategyId
    side: Literal['BUY', 'SELL']
    units: WholeUnits
    expected_price_version: str = Field(min_length=1, max_length=128)


class DecisionReport(Contract):
    request_id: UUID
    action: Literal['HOLD', 'BUY', 'SELL']
    explanation: SafeText | None = None
    trade_id: UUID | None = None

    @model_validator(mode='after')
    def linked_execution(self):
        if (self.action == 'HOLD') != (self.trade_id is None):
            raise ValueError('HOLD has no trade; BUY/SELL reports must link an existing trade receipt')
        return self


class TradeReceipt(Contract):
    trade_id: UUID
    request_id: UUID
    strategy_id: StrategyId
    side: Literal['BUY', 'SELL']
    units: WholeUnits
    status: Literal['SETTLED']
    unit_price: Decimal = Field(ge=0)
    price_version: str
    price_source_version: str
    price_valued_at: datetime
    price_provenance: str
    currency: Literal['USD']
    gross_amount: Decimal = Field(ge=0)
    fee: Decimal = Field(ge=0)
    owned_units_after: int = Field(ge=0, strict=True)
    available_units_before: int = Field(ge=0, strict=True)
    available_units_after: int = Field(ge=0, strict=True)
    funding_reference: UUID
    executed_at: datetime


class ErrorEnvelope(Contract):
    code: str
    message: str
    retryable: bool
    request_id: UUID | None = None


class FeedbackRequest(Contract):
    request_id: UUID
    agent_ids: list[UUID] = Field(min_length=1, max_length=100)
    message: SafeText


class ActivityRecord(Contract):
    cursor: int = Field(ge=1, strict=True)
    event_id: UUID
    occurred_at: datetime
    agent_id: UUID | None
    owner_id: UUID | None = None
    operation: str
    status_code: int = Field(ge=100, le=599)
    outcome: Literal['success', 'rejected', 'error']
    request_id: UUID | None
    resource_id: str | None = None


class QueryRequest(Contract):
    request_id: UUID
    revision: int = Field(default=0, ge=0, strict=True)
    kind: str = Field(min_length=1, max_length=128)
    strategy_ids: list[StrategyId] = Field(default_factory=list, max_length=1000)
    window_start: datetime | None = None
    window_end: datetime | None = None
    limit: int = Field(default=5, gt=0, strict=True)

    @model_validator(mode='after')
    def valid_window(self):
        for value in (self.window_start, self.window_end):
            if value is not None and value.tzinfo is None:
                raise ValueError('Query timestamps require timezone')
        if self.window_start and self.window_end and self.window_start > self.window_end:
            raise ValueError('Query start must not follow end')
        return self


class QueryDelivery(Contract):
    delivery_id: UUID
    request_id: UUID
    revision: int = Field(ge=0, strict=True)
    result_version: UUID
    created_at: datetime
    source_version: str
    mode: Literal['simulated_random', 'external']
    strategy_ids: list[StrategyId]
    query: QueryRequest
    notice: str


def fingerprint(value: Contract) -> str:
    return sha256(json.dumps(value.model_dump(mode='json'), sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def assert_same_request(original: Contract, retry: Contract) -> None:
    if fingerprint(original) != fingerprint(retry):
        raise ValueError('REQUEST_ID_CONFLICT')


def schema_catalogue():
    models = (ConnectionRequest, TradeRequest, DecisionReport, TradeReceipt, ErrorEnvelope,
              FeedbackRequest, ActivityRecord, QueryRequest, QueryDelivery)
    return {model.__name__: model.model_json_schema() for model in models}
