"""Reproducible performance, risk and behaviour metrics.

VERSION HISTORY
v1.0.1 (2026-09-04) - Relocated from epics/ep_051_strategy_directory/hosted_directory/ to epics/ep_049_strategy_intelligence/hosted_directory/ per Ed's EP049 ownership decision. No code changes.
v1.2.0 · 2026-08-27 · Adds confidence_components(): breaks evidence confidence into sample size, period coverage, concentration and chronological holdout stability, degrading gracefully when only trade_count/years are available.
v1.1.0 · 2026-08-24 · Adds capital-aware CAGR, historical VaR and calendar period returns.
v1.0.0 · 2026-08-24 · Golden-testable annualisation, risk-adjusted and behavioural metrics.
"""
from __future__ import annotations
import math
import statistics
from datetime import datetime

METHOD_VERSION = "1.0.0"


def _finite(value: float | None) -> float | None:
    return value if value is not None and math.isfinite(value) else None


def evidence_years(start: datetime | None, end: datetime | None) -> float:
    if not start or not end or end <= start: return 0.0
    return (end - start).total_seconds() / (365.2425 * 86400)


def calculate(returns: list[float], timestamps: list[datetime] | None = None,starting_capital:float|None=None) -> dict[str, float | None]:
    values = [float(x) for x in returns if math.isfinite(float(x))]
    if not values:
        return {key: None for key in ("total_return","annualized_return","cagr","value_at_risk_95","volatility","max_drawdown","downside_deviation","sharpe","sortino","calmar","win_rate","profit_factor","expectancy","trades_per_year")}
    total = sum(values); wins=[x for x in values if x>0]; losses=[x for x in values if x<0]
    years=evidence_years(min(timestamps),max(timestamps)) if timestamps else 0.0
    trades_per_year=len(values)/years if years>0 else None
    annualized=total/years if years>0 else None
    ending_capital=float(starting_capital)+total if starting_capital is not None else None
    cagr=(ending_capital/float(starting_capital))**(1/years)-1 if years>0 and starting_capital and ending_capital and ending_capital>0 else None
    ordered=sorted(values);var_index=max(0,math.ceil(.05*len(ordered))-1);var95=ordered[var_index]
    scale=math.sqrt(trades_per_year) if trades_per_year and trades_per_year>0 else 1.0
    vol=statistics.stdev(values)*scale if len(values)>1 else 0.0
    downside=[min(0.0,x) for x in values]
    downside_dev=math.sqrt(sum(x*x for x in downside)/len(downside))*scale
    mean=statistics.mean(values)*scale*scale
    sharpe=mean/vol if vol else None; sortino=mean/downside_dev if downside_dev else None
    equity=0.0; peak=0.0; max_dd=0.0
    for value in values:
        equity += value; peak=max(peak,equity); max_dd=min(max_dd,equity-peak)
    calmar=annualized/abs(max_dd) if annualized is not None and max_dd else None
    gross_profit=sum(wins); gross_loss=abs(sum(losses))
    return {"total_return":total,"annualized_return":_finite(annualized),"cagr":_finite(cagr),"value_at_risk_95":_finite(var95),"volatility":_finite(vol),"max_drawdown":max_dd,
            "downside_deviation":_finite(downside_dev),"sharpe":_finite(sharpe),"sortino":_finite(sortino),"calmar":_finite(calmar),
            "win_rate":len(wins)/len(values),"profit_factor":gross_profit/gross_loss if gross_loss else None,
            "expectancy":statistics.mean(values),"trades_per_year":_finite(trades_per_year)}


CONFIDENCE_WEIGHTS={"sample_size":0.35,"period_coverage":0.15,"concentration":0.25,"holdout_stability":0.25}
CONFIDENCE_METHOD_VERSION="1.1.0"


def confidence_components(trade_count:int,years:float,returns:list[float]|None=None,timestamps:list[datetime]|None=None)->dict:
    """Evidence confidence broken into its named components, degrading gracefully
    when only trade_count/years are known (e.g. the fast aggregate profile path)."""
    sample_size=min(1.0,trade_count/200.0); period_coverage=min(1.0,years/3.0)
    concentration=None; holdout_stability=None
    values=[float(x) for x in (returns or []) if math.isfinite(float(x))]
    if len(values)>=5:
        magnitudes=[abs(x) for x in values]; total=sum(magnitudes)
        concentration=1.0-(max(magnitudes)/total) if total else None
    if len(values)>=10 and timestamps and len(timestamps)==len(returns):
        paired=sorted(zip(timestamps,values),key=lambda pair:pair[0]); ordered=[value for _,value in paired]
        mid=len(ordered)//2; first,second=ordered[:mid],ordered[mid:]
        mean_first=statistics.mean(first); mean_second=statistics.mean(second); denom=abs(mean_first)+abs(mean_second)
        holdout_stability=1.0-min(1.0,abs(mean_first-mean_second)/denom) if denom else 1.0
    available={"sample_size":sample_size,"period_coverage":period_coverage}
    if concentration is not None:available["concentration"]=concentration
    if holdout_stability is not None:available["holdout_stability"]=holdout_stability
    weight_total=sum(CONFIDENCE_WEIGHTS[key] for key in available)
    overall=sum(available[key]*CONFIDENCE_WEIGHTS[key] for key in available)/weight_total if weight_total else 0.0
    return {"confidence":round(overall,4),"sample_size":round(sample_size,4),"period_coverage":round(period_coverage,4),
            "concentration":round(concentration,4) if concentration is not None else None,
            "holdout_stability":round(holdout_stability,4) if holdout_stability is not None else None,
            "weights":CONFIDENCE_WEIGHTS,"components_available":sorted(available),"methodology_version":CONFIDENCE_METHOD_VERSION}


def evidence_confidence(trade_count: int, years: float, returns:list[float]|None=None, timestamps:list[datetime]|None=None) -> float:
    return confidence_components(trade_count,years,returns,timestamps)["confidence"]


def period_returns(returns:list[float],timestamps:list[datetime])->dict:
    monthly={};annual={}
    for value,stamp in zip(returns,timestamps):
        monthly[stamp.strftime("%Y-%m")]=monthly.get(stamp.strftime("%Y-%m"),0)+float(value)
        annual[str(stamp.year)]=annual.get(str(stamp.year),0)+float(value)
    return {"monthly":monthly,"annual":annual,"unit":"money","methodology_version":METHOD_VERSION}
