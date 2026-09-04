"""Build Strategy Intelligence Profiles from canonical aggregates and trade returns.

VERSION HISTORY
v1.0.1 (2026-09-04) - Relocated from epics/ep_051_strategy_directory/hosted_directory/ to epics/ep_049_strategy_intelligence/hosted_directory/ per Ed's EP049 ownership decision. No code changes.
v1.2.0 · 2026-08-27 · Populates EvidenceProfile.confidence_components (sample size, period coverage, concentration, holdout stability) using confidence_components() instead of the sample+duration-only evidence_confidence().
v1.1.0 · 2026-08-24 · Adds capital-aware metrics, calendar returns and trade-behaviour evidence.
v1.0.0 · 2026-08-24 · Server-side profile construction with evidence and methodology provenance.
"""
from __future__ import annotations
from datetime import datetime, timezone
from .metrics import METHOD_VERSION, calculate, confidence_components, evidence_years
from .models import EvidenceProfile, IntelligenceMetrics, MetricValue, StrategyClassification, StrategyIdentity, StrategyIntelligenceProfile
from .metrics import period_returns
from .robustness import divergence_split_from_points,live_backtest_divergence,parameter_sensitivity,trade_behaviour,walk_forward,walk_forward_folds_from_points

UNITS={"total_return":"money","annualized_return":"money/year","cagr":"fraction/year","value_at_risk_95":"money/trade","volatility":"money/year","max_drawdown":"money",
       "downside_deviation":"money/year","sharpe":"ratio","sortino":"ratio","calmar":"ratio","win_rate":"fraction",
       "profit_factor":"ratio","expectancy":"money/trade","trades_per_year":"trades/year"}


def outcomes(points:list[dict],return_basis:str="net_return")->list[float]:
    """Extract the selected outcome column from trade points, skipping rows
    where that basis wasn't recorded (e.g. alt_net_return is nullable) rather
    than treating a missing value as zero."""
    return [float(p[return_basis]) for p in points if p.get(return_basis) is not None]


def build_profile(summary: dict, points: list[dict], return_basis: str = "net_return") -> StrategyIntelligenceProfile:
    valid_points=[p for p in points if p.get(return_basis) is not None]
    timestamps=[datetime.fromisoformat(p["closed_at"]) for p in valid_points if p.get("closed_at")]
    start=min(timestamps) if timestamps else None; end=max(timestamps) if timestamps else None
    returns=outcomes(valid_points,return_basis)
    computed=calculate(returns,timestamps,summary.get("starting_capital"))
    years=evidence_years(start,end); count=len(valid_points); state="VALID" if count>=30 else "COLLECTING" if count else "UNAVAILABLE"
    def metric(key): return MetricValue(value=computed[key],unit=UNITS[key],methodology_version=METHOD_VERSION,evidence_state=state if computed[key] is not None else "UNAVAILABLE",source=f"combined_trades_closed.{return_basis}")
    instruments=[x.strip() for x in (summary.get("product_name") or "").split(",") if x.strip()]
    confidence=confidence_components(count,years,returns,timestamps)
    return StrategyIntelligenceProfile(generated_at=datetime.now(timezone.utc),
      identity=StrategyIdentity(strategy_id=summary["strategy_id"],name=summary.get("descriptive_name"),author=summary.get("author"),source=summary.get("source") or "DNA",version=str(summary.get("definition_version") or "1"),description=summary.get("description")),
      classification=StrategyClassification(asset_class=summary.get("market") or "FX",instruments=instruments,strategy_family=summary.get("strategy_family"),timeframe=summary.get("timeframe"),direction=summary.get("direction") or "both",parameters=summary.get("parameters") or {}),
      metrics=IntelligenceMetrics(**{key:metric(key) for key in UNITS}),
      evidence=EvidenceProfile(trade_count=count,start=start,end=end,years=years,quality_state=state,
                               confidence=confidence["confidence"],confidence_components=confidence,freshness="CURRENT" if end else "UNKNOWN"),
      robustness={"trade_behaviour":trade_behaviour(valid_points),"period_returns":period_returns(returns,timestamps),
                  "parameter_sensitivity":parameter_sensitivity(summary.get("parameter_runs") or []),
                  "walk_forward":walk_forward(summary.get("walk_forward_folds") or walk_forward_folds_from_points(valid_points,return_basis=return_basis)),
                  "live_backtest_divergence":live_backtest_divergence(*(([summary["backtest_returns"],summary["live_returns"]]) if summary.get("backtest_returns") and summary.get("live_returns") else divergence_split_from_points(valid_points,return_basis=return_basis))),
                  "series_window":{"returned_points":count,"maximum_points":1000,"truncated":count>=1000}},
      links={"directory":"/","equity_curve":f"/api/dna/strategies/{summary['strategy_id']}/equity-curve",
             "detail":f"/strategy.html?id={summary['strategy_id']}"},
      methodology={"metric_registry":METHOD_VERSION,"outcome":f"signed {return_basis}","cost_basis":"costs and commission included","return_basis":return_basis})


def build_summary_profile(summary:dict)->StrategyIntelligenceProfile:
    """Fast exact aggregate profile; sequence-dependent metrics fail closed until a full series is warmed."""
    profile=build_profile(summary,[]);start=summary.get("evidence_start");end=summary.get("evidence_end")
    start=datetime.fromisoformat(str(start).replace("Z","+00:00")) if start else None;end=datetime.fromisoformat(str(end).replace("Z","+00:00")) if end else None
    count=int(summary.get("total_trades") or 0);years=evidence_years(start,end);state="VALID" if count>=30 else "COLLECTING" if count else "UNAVAILABLE";total=float(summary.get("total_net_return") or 0)
    values={"total_return":total,"annualized_return":total/years if years else None,"win_rate":summary.get("win_rate"),"profit_factor":summary.get("profit_factor"),"expectancy":total/count if count else None,"trades_per_year":count/years if years else None}
    for name,value in values.items():metric=getattr(profile.metrics,name);metric.value=float(value) if value is not None else None;metric.evidence_state=state if value is not None else "UNAVAILABLE";metric.source="combined_trades_closed aggregate"
    confidence=confidence_components(count,years)
    profile.evidence=EvidenceProfile(trade_count=count,start=start,end=end,years=years,quality_state=state,confidence=confidence["confidence"],confidence_components=confidence,freshness="CURRENT" if end else "UNKNOWN")
    profile.robustness={"series_window":{"state":"WARMUP_REQUIRED","returned_points":0},"period_returns":{"state":"UNAVAILABLE"}}
    profile.methodology["profile_depth"]="aggregate-safe; sequence metrics unavailable"
    return profile
