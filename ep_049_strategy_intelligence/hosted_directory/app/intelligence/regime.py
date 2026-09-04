"""Point-in-time market regime and strategy suitability engines.

VERSION HISTORY
v1.0.1 (2026-09-04) - Relocated from epics/ep_051_strategy_directory/hosted_directory/ to epics/ep_049_strategy_intelligence/hosted_directory/ per Ed's EP049 ownership decision. No code changes.
v1.0.0 · 2026-08-24 · Deterministic regime classification, profiles and explainable suitability ranking.
"""
from __future__ import annotations
from collections import defaultdict
import math,statistics

CALIBRATION_VERSION="ecb-next-day-direction-2026-08-v1"
CALIBRATED_DIRECTION_PERSISTENCE={0:.9916666667,1:.9647887324,2:.8536585366,3:.8888888889,4:.5}


def classify(features:dict)->dict:
    required=("trend","volatility_z","drawdown")
    missing=[x for x in required if features.get(x) is None]
    if missing:return {"state":"UNKNOWN","confidence":0,"missing":missing,"version":"1.0.0"}
    trend=float(features["trend"]);vol=float(features["volatility_z"]);dd=float(features["drawdown"])
    if any(not math.isfinite(value) for value in (trend,vol,dd)):return {"state":"UNKNOWN","confidence":0,"reason":"NONFINITE","version":"1.1.0"}
    direction="bull" if trend>.02 and dd>-.1 else "bear" if trend<-.02 or dd<=-.1 else "sideways";trend_state="trending" if abs(trend)>.02 else "sideways"
    volatility="high volatility" if vol>=.75 else "low volatility" if vol<=-.75 else "normal volatility"
    margin=min(1.0,.5+abs(trend)*5+abs(vol)*.1);bin_index=min(4,max(0,int((margin-.5)/.1)))
    probability=round(CALIBRATED_DIRECTION_PERSISTENCE[bin_index],3);other=(1-probability)/2;probabilities={"bull":other,"bear":other,"sideways":other};probabilities[direction]=probability
    return {"state":f"{direction} / {volatility}","direction":direction,"trend_state":trend_state,"volatility":volatility,"confidence":probability,"probabilities":probabilities,"model_margin":round(margin,3),"calibration_version":CALIBRATION_VERSION,"version":"1.2.0"}


def strategy_regime_profile(observations:list[dict],minimum=5)->dict:
    groups=defaultdict(list)
    for row in observations:
        value=float(row["return"])
        if math.isfinite(value):groups[row["regime"]].append(value)
    out={}
    for regime,values in groups.items():
        count=len(values);mean=statistics.mean(values);stdev=statistics.stdev(values) if count>1 else 0;margin=1.96*stdev/math.sqrt(count) if count else 0;equity=peak=0;drawdown=0
        for value in values:equity+=value;peak=max(peak,equity);drawdown=min(drawdown,equity-peak)
        out[regime]={"count":count,"mean_return":mean,"positive_rate":sum(x>0 for x in values)/count,"volatility":stdev,"max_drawdown":drawdown,"confidence_interval_95":[mean-margin,mean+margin],
          "confidence":"VALID" if count>=minimum else "COLLECTING"}
    return out


def recommend(current:dict,candidates:list[dict],risk_limit:float|None=None)->list[dict]:
    if current.get("state")=="UNKNOWN" or current.get("confidence",0)<.5:return []
    regime=current["state"];results=[]
    for candidate in candidates:
        evidence=candidate.get("regimes",{}).get(regime)
        if not evidence or evidence.get("confidence")!="VALID":continue
        if risk_limit is not None and abs(candidate.get("max_drawdown",0))>risk_limit:continue
        quality=float(candidate.get("quality_score",0));fit=max(0,min(100,50+evidence["mean_return"]*10));score=.6*quality+.4*fit
        counter=[] if evidence["positive_rate"]>=.5 else ["Positive rate below 50%"]
        if evidence.get("confidence_interval_95",[0,0])[0]<=0:counter.append("95% interval includes a non-positive mean return")
        results.append({"strategy_id":candidate["strategy_id"],"suitability_score":round(score,2),"why":[f"Quality score {quality:.1f}",f"Mean return {evidence['mean_return']:.3f} in {regime}",f"Current-regime confidence {current['confidence']:.2f}"],"counter_evidence":counter,"evidence":{"regime":regime,"sample_count":evidence.get("count"),"confidence_interval_95":evidence.get("confidence_interval_95"),"profile_version":"1.1.0"}})
    return sorted(results,key=lambda x:x["suitability_score"],reverse=True)
