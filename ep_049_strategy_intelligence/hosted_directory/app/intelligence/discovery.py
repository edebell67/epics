"""Canonical structured and natural-language strategy discovery.

VERSION HISTORY
v1.0.1 (2026-09-04) - Relocated from epics/ep_051_strategy_directory/hosted_directory/ to epics/ep_049_strategy_intelligence/hosted_directory/ per Ed's EP049 ownership decision. No code changes.
v1.3.0 · 2026-08-27 · why_matched reasons now include the actual stored evidence value that satisfied each constraint (evidence_value()), not just the constraint threshold, so every statement traces to a concrete metric/classification value.
v1.2.0 · 2026-08-27 · Adds evidence_confidence as a selectable sort/rank objective (rank_value() replaces the ad-hoc quality_score special-case with a small dispatch covering quality_score, evidence_confidence and plain metrics).
v1.1.0 · 2026-08-24 · Adds explicit units, full classification/evidence constraints and exclusion traces.
v1.0.0 · 2026-08-24 · Validated query plan, deterministic interpreter, retrieval and explanations.
"""
from __future__ import annotations
import re
import hashlib,json
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrategyQuery(BaseModel):
    model_config=ConfigDict(extra="forbid")
    asset_class: str | None = Field(None,max_length=40)
    instrument: str | None = Field(None,max_length=80)
    strategy_family: str | None = Field(None,max_length=80)
    timeframe: str | None = Field(None,max_length=40)
    trade_direction: Literal["long","short","both"] | None = None
    min_win_rate: float | None = Field(None,ge=0,le=1)
    min_annualized_return: float | None = None
    annualized_return_unit: Literal["fraction/year","money/year"] | None = None
    max_drawdown: float | None = Field(None,ge=0)
    max_drawdown_unit: Literal["fraction","money"] | None = None
    min_sharpe: float | None = None
    min_profit_factor: float | None = Field(None,ge=0)
    min_evidence_confidence: float | None = Field(None,ge=0,le=1)
    min_quality_score: float | None = Field(None,ge=0,le=100)
    min_track_record_years: float | None = Field(None,ge=0)
    min_sortino: float | None = None
    min_calmar: float | None = None
    min_value_at_risk_95: float | None = None
    min_walk_forward_positive_fold_rate: float | None = Field(None,ge=0,le=1)
    require_no_divergence_alert: bool | None = None
    require_parameter_stable: bool | None = None
    min_trade_count: int | None = Field(None,ge=0,description="Minimum closed trades within the evidence window (lookback_hours if set, else since inception).")
    lookback_hours: float | None = Field(None,gt=0,le=8760,description=
        "Restrict the evidence window to the trailing N hours from now, instead of "
        "since-inception - e.g. lookback_hours=3 + min_trade_count=6 answers 'top "
        "performers in the last 3 hours with more than 5 trades'. Local SQL Server "
        "backend only. Every metric/filter/rank is recomputed from just that window.")
    return_basis: Literal["net_return","alt_net_return"] = Field("net_return",
        description="Outcome column every metric, robustness check and rank is computed from. "
                    "net_return is the trade as actually taken; alt_net_return is the same trade "
                    "reversed (opposite side), letting a query ask 'would fading this strategy have worked'.")
    regime: str | None = Field(None,max_length=80)
    sort: Literal["quality_score","annualized_return","win_rate","sharpe","sortino","calmar","max_drawdown","evidence_confidence"] = "quality_score"
    direction: Literal["asc","desc"] = "desc"

    @model_validator(mode="after")
    def validate_units(self):
        if self.annualized_return_unit and self.min_annualized_return is None:raise ValueError("annualized_return_unit requires min_annualized_return")
        if self.max_drawdown_unit and self.max_drawdown is None:raise ValueError("max_drawdown_unit requires max_drawdown")
        if self.min_annualized_return is not None and self.annualized_return_unit is None:raise ValueError("min_annualized_return requires annualized_return_unit")
        if self.max_drawdown is not None and self.max_drawdown_unit is None:raise ValueError("max_drawdown requires max_drawdown_unit")
        return self


class NaturalLanguageRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    query: str = Field(min_length=3,max_length=500)


def interpret(text:str)->StrategyQuery:
    lowered=text.lower(); values={}
    assets={"equity":"equity","equities":"equity","stock":"equity","stocks":"equity","fx":"FX","forex":"FX","crypto":"crypto"}
    for word,value in assets.items():
        if re.search(rf"\b{word}\b",lowered):values["asset_class"]=value;break
    patterns=(
      ("min_win_rate",r"(?:win rate|winning)[^\d]{0,20}(?:above|over|at least|>=|>)?\s*(\d+(?:\.\d+)?)\s*%",lambda x:float(x)/100),
      ("min_annualized_return",r"(?:annual(?:ized)? return|return)[^\d-]{0,20}(?:above|over|more than|at least|>=|>)?\s*(-?\d+(?:\.\d+)?)\s*%",lambda x:float(x)/100),
      ("max_drawdown",r"(?:drawdown)[^\d]{0,20}(?:below|under|less than|at most|<=|<)?\s*(\d+(?:\.\d+)?)\s*%",lambda x:float(x)/100),
      ("min_sharpe",r"sharpe[^\d-]{0,15}(?:above|over|at least|>=|>)?\s*(-?\d+(?:\.\d+)?)",float),
      ("min_track_record_years",r"(?:at least\s*)?(\d+(?:\.\d+)?)\s*years?(?:\s+of)?(?:\s+backtest|\s+track record|\s+history|\s+evidence)",float),
    )
    for key,pattern,convert in patterns:
        match=re.search(pattern,lowered)
        if match:values[key]=convert(match.group(1))
    if "min_annualized_return" in values:values["annualized_return_unit"]="fraction/year"
    if "max_drawdown" in values:values["max_drawdown_unit"]="fraction"
    for regime in ("bull","bear","trending","sideways","high volatility","low volatility"):
        if regime in lowered:values["regime"]=regime;break
    return StrategyQuery(**values)


def interpret_with_trace(text:str)->dict:
    plan=interpret(text);fields=plan.model_dump(exclude_defaults=True,exclude_none=True);constraints=[key for key in fields if key not in {"sort","direction"}]
    unsupported=[]
    for marker in ("guaranteed","execute trade","place order","ignore instructions","system prompt"):
        if marker in text.lower():unsupported.append(marker)
    confidence=round(min(.98,.45+.09*len(constraints)),2) if constraints else .25
    clarifications=[] if constraints else ["Add an asset, performance, risk, evidence or regime constraint."]
    if unsupported:clarifications.append("Unsupported execution or guarantee language was ignored; this finder only produces a validated evidence query.")
    canonical=json.dumps(plan.model_dump(mode="json"),sort_keys=True,separators=(",",":"));return {"plan":plan,"confidence":confidence,"clarifications":clarifications,"unsupported_terms":unsupported,"plan_sha256":hashlib.sha256(canonical.encode()).hexdigest(),"interpreter_version":"1.1.0"}


def matches(profile:dict,plan:StrategyQuery)->tuple[bool,list[str]]:
    reasons=[]; classification=profile["classification"]; metrics=profile["metrics"]; evidence=profile["evidence"]
    value=lambda key:metrics.get(key,{}).get("value")
    unit=lambda key:metrics.get(key,{}).get("unit")
    score=profile.get("score",{});regimes=profile.get("regimes",{});robustness=profile.get("robustness",{})
    walk_forward=robustness.get("walk_forward",{}) or {};divergence=robustness.get("live_backtest_divergence",{}) or {};sensitivity=robustness.get("parameter_sensitivity",{}) or {}
    checks=[
      (plan.asset_class,classification.get("asset_class"),lambda a,b:str(a).lower()==str(b).lower(),"asset class"),
      (plan.instrument,classification.get("instruments",[]),lambda a,b:str(a).lower() in [str(x).lower() for x in b],"instrument"),
      (plan.strategy_family,classification.get("strategy_family"),lambda a,b:b is not None and str(a).lower()==str(b).lower(),"strategy family"),
      (plan.timeframe,classification.get("timeframe"),lambda a,b:b is not None and str(a).lower()==str(b).lower(),"timeframe"),
      (plan.trade_direction,classification.get("direction"),lambda a,b:b is not None and (a==b or b=="both"),"trade direction"),
      (plan.min_win_rate,value("win_rate"),lambda a,b:b is not None and b>=a,"win rate"),
      (plan.min_annualized_return,value("annualized_return"),lambda a,b:b is not None and unit("annualized_return")==plan.annualized_return_unit and b>=a,"annualized return"),
      (plan.max_drawdown,value("max_drawdown"),lambda a,b:b is not None and unit("max_drawdown")==plan.max_drawdown_unit and abs(b)<=a,"maximum drawdown"),
      (plan.min_sharpe,value("sharpe"),lambda a,b:b is not None and b>=a,"Sharpe"),
      (plan.min_sortino,value("sortino"),lambda a,b:b is not None and b>=a,"Sortino"),
      (plan.min_calmar,value("calmar"),lambda a,b:b is not None and b>=a,"Calmar"),
      (plan.min_value_at_risk_95,value("value_at_risk_95"),lambda a,b:b is not None and b>=a,"95% VaR"),
      (plan.min_profit_factor,value("profit_factor"),lambda a,b:b is not None and b>=a,"profit factor"),
      (plan.min_track_record_years,evidence.get("years"),lambda a,b:b is not None and b>=a,"track record"),
      (plan.min_trade_count,evidence.get("trade_count"),lambda a,b:b is not None and b>=a,"trade count"),
      (plan.min_evidence_confidence,evidence.get("confidence"),lambda a,b:b is not None and b>=a,"evidence confidence"),
      (plan.min_quality_score,score.get("quality_score"),lambda a,b:b is not None and b>=a,"quality score"),
      (plan.min_walk_forward_positive_fold_rate,walk_forward,lambda a,b:b.get("state")=="VALID" and b.get("positive_fold_rate") is not None and b["positive_fold_rate"]>=a,"walk-forward positive-fold rate"),
      (plan.require_no_divergence_alert,divergence,lambda a,b:(not a) or (b.get("state")=="VALID" and b.get("alert") is False),"live/backtest divergence"),
      (plan.require_parameter_stable,sensitivity,lambda a,b:(not a) or (b.get("state")=="VALID" and b.get("stable") is True),"parameter sensitivity"),
      (plan.regime,regimes,lambda a,b:any(str(a).lower() in str(key).lower() and item.get("confidence")=="VALID" for key,item in b.items()),"regime"),
    ]
    for expected,actual,predicate,label in checks:
        if expected is None:continue
        if not predicate(expected,actual):return False,[f"{label} did not satisfy {expected}"]
        reasons.append(f"{label} {evidence_value(label,actual,expected)} satisfies constraint {expected}")
    return True,reasons


def evidence_value(label,actual,expected):
    """Render the stored evidence that made a check pass, so every why-matched
    statement traces to a concrete metric/classification value, not just the
    query constraint that was checked against it."""
    if label=="instrument":
        return next((item for item in actual if str(item).lower()==str(expected).lower()),actual)
    if label=="regime":
        return next((key for key,item in actual.items() if str(expected).lower() in str(key).lower() and item.get("confidence")=="VALID"),expected)
    if label=="walk-forward positive-fold rate":return actual.get("positive_fold_rate")
    if label=="live/backtest divergence":return {"state":actual.get("state"),"alert":actual.get("alert"),"mean_shift":actual.get("mean_shift")}
    if label=="parameter sensitivity":return {"state":actual.get("state"),"stable":actual.get("stable"),"score_cv":actual.get("score_cv")}
    if isinstance(actual,float):return round(actual,4)
    return actual


def rank_value(profile,metric):
    if metric=="quality_score":return profile.get("score",{}).get("quality_score")
    if metric=="evidence_confidence":return profile.get("evidence",{}).get("confidence")
    return value_for_rank(profile,metric)


def retrieve(profiles:list[dict],plan:StrategyQuery)->list[dict]:
    results=[]
    for profile in profiles:
        valid,reasons=matches(profile,plan)
        if valid:results.append({"profile":profile,"why_matched":reasons,"rank_trace":{"objective":plan.sort,"direction":plan.direction,"value":rank_value(profile,plan.sort),"evidence_eligible":profile.get("score",{}).get("rank_eligible",True)}})
    def sort_value(item):
        value=rank_value(item["profile"],plan.sort)
        return value if value is not None else float("inf") if plan.direction=="asc" else float("-inf")
    eligible=[item for item in results if item["profile"].get("score",{}).get("rank_eligible",True)]
    ineligible=[item for item in results if not item["profile"].get("score",{}).get("rank_eligible",True)]
    reverse=plan.direction=="desc"
    return sorted(eligible,key=sort_value,reverse=reverse)+sorted(ineligible,key=sort_value,reverse=reverse)


def value_for_rank(profile,metric):return profile.get("metrics",{}).get(metric,{}).get("value")


def facet_counts(profiles):
    output={key:{} for key in ("asset_class","strategy_family","timeframe","direction","instrument")}
    for profile in profiles:
        classification=profile.get("classification",{})
        for key in ("asset_class","strategy_family","timeframe","direction"):
            value=classification.get(key)
            if value is not None:output[key][str(value)]=output[key].get(str(value),0)+1
        for value in classification.get("instruments",[]):output["instrument"][str(value)]=output["instrument"].get(str(value),0)+1
    return output


def chain(profiles:list[dict],plans:list[StrategyQuery])->dict:
    """Apply a sequence of query plans as a narrowing funnel: each stage's
    survivors become the candidate pool for the next stage. Reuses retrieve()
    per stage so filter/rank/why-matched semantics stay identical to a single
    query, and reports per-stage elimination so a caller (human or agent) can
    see which criterion was the bottleneck."""
    pool=profiles;stages=[];last_results=[]
    for index,plan in enumerate(plans):
        results=retrieve(pool,plan);survivors=[item["profile"] for item in results];survivor_ids={s["identity"]["strategy_id"] for s in survivors}
        stages.append({"index":index,"plan":plan.model_dump(mode="json"),"input_count":len(pool),"survivor_count":len(survivors),
                        "eliminated_count":len(pool)-len(survivors),"eliminated_sample":[p["identity"]["strategy_id"] for p in pool if p["identity"]["strategy_id"] not in survivor_ids][:10]})
        pool=survivors;last_results=results
    return {"stages":stages,"final_count":len(pool),"items":last_results}


def exclusion_trace(profiles:list[dict],plan:StrategyQuery)->list[dict]:
    included={item["profile"]["identity"]["strategy_id"] for item in retrieve(profiles,plan)};output=[]
    for profile in profiles:
        strategy_id=profile["identity"]["strategy_id"]
        if strategy_id not in included:
            _,reasons=matches(profile,plan);output.append({"strategy_id":strategy_id,"reason":reasons[0] if reasons else "one or more hard constraints were not satisfied"})
    return output
