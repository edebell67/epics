"""Canonical Strategy Intelligence Object contracts.

VERSION HISTORY
v1.0.1 (2026-09-04) - Relocated from epics/ep_051_strategy_directory/hosted_directory/ to epics/ep_049_strategy_intelligence/hosted_directory/ per Ed's EP049 ownership decision. No code changes.
v1.2.0 · 2026-08-27 · Adds optional EvidenceProfile.confidence_components for the sample-size/period-coverage/concentration/holdout-stability breakdown.
v1.1.0 · 2026-08-24 · Adds CAGR, VaR and extensible robustness evidence.
v1.0.0 · 2026-08-24 · Versioned identity, classification, metrics, evidence and provenance schemas.
"""
from __future__ import annotations
from datetime import datetime
import math
from typing import Any, Literal
from pydantic import BaseModel, Field,field_validator


class MetricValue(BaseModel):
    value: float | None
    unit: str
    methodology_version: str = "1.0.0"
    evidence_state: Literal["VALID", "COLLECTING", "UNAVAILABLE"] = "VALID"
    source: str = "combined_trades_closed.net_return"

    @field_validator("value")
    @classmethod
    def finite_value(cls,value):
        if value is not None and not math.isfinite(float(value)):raise ValueError("metric evidence must be finite")
        return value


class StrategyIdentity(BaseModel):
    strategy_id: str = Field(pattern=r"^DNA_[A-Za-z0-9]+$")
    name: str | None = None
    author: str | None = None
    source: str = "DNA"
    version: str = "1"
    description: str | None = None


class StrategyClassification(BaseModel):
    asset_class: str = "FX"
    instruments: list[str] = Field(default_factory=list)
    strategy_family: str | None = None
    timeframe: str | None = None
    direction: Literal["long", "short", "both", "unknown"] = "both"
    parameters: dict[str, Any] = Field(default_factory=dict)


class EvidenceProfile(BaseModel):
    trade_count: int
    start: datetime | None = None
    end: datetime | None = None
    years: float = 0
    quality_state: Literal["VALID", "COLLECTING", "UNAVAILABLE"]
    confidence: float = Field(ge=0, le=1)
    confidence_components: dict[str, Any] | None = None
    freshness: Literal["CURRENT", "STALE", "UNKNOWN"] = "UNKNOWN"


class IntelligenceMetrics(BaseModel):
    total_return: MetricValue
    annualized_return: MetricValue
    cagr: MetricValue
    value_at_risk_95: MetricValue
    volatility: MetricValue
    max_drawdown: MetricValue
    downside_deviation: MetricValue
    sharpe: MetricValue
    sortino: MetricValue
    calmar: MetricValue
    win_rate: MetricValue
    profit_factor: MetricValue
    expectancy: MetricValue
    trades_per_year: MetricValue


class StrategyIntelligenceProfile(BaseModel):
    schema_version: str = "1.0.0"
    generated_at: datetime
    identity: StrategyIdentity
    classification: StrategyClassification
    metrics: IntelligenceMetrics
    evidence: EvidenceProfile
    robustness: dict[str, Any] = Field(default_factory=dict)
    links: dict[str, str]
    methodology: dict[str, str]
