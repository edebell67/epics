"""Explainable comparative intelligence: scores, cohorts, correlations and similarity.

VERSION HISTORY
v1.0.1 (2026-09-04) - Relocated from epics/ep_051_strategy_directory/hosted_directory/ to epics/ep_049_strategy_intelligence/hosted_directory/ per Ed's EP049 ownership decision. No code changes.
v1.1.0 · 2026-08-24 · Adds classified cohorts, minimum-size suppression and timestamp-aligned correlation.
v1.0.0 · 2026-08-24 · Versioned composite scoring and relationship engines.
"""
from __future__ import annotations
import math, statistics

SCORE_VERSION="1.1.0"
WEIGHTS={"performance":0.25,"risk":0.20,"consistency":0.20,"robustness":0.15,"evidence":0.20}
SCORE_SPEC={"version":SCORE_VERSION,"range":[0,100],"missing_policy":"zero contribution; confidence remains visible","weights":WEIGHTS,
 "components":{"performance":["annualized_return","profit_factor"],"risk":["max_drawdown","volatility"],"consistency":["sharpe","sortino"],"robustness":["walk_forward","live_backtest_divergence"],"evidence":["trade_count","track_record_years"]}}


def _bounded(value,low,high):
    if value is None:return 0.0
    return max(0.0,min(100.0,(float(value)-low)/(high-low)*100))


def score_profile(profile:dict)->dict:
    metrics=profile["metrics"]; evidence=profile["evidence"]
    val=lambda name: metrics[name]["value"]
    performance=(_bounded(val("annualized_return"),-10000,10000)+_bounded(val("profit_factor"),0,2.5))/2
    risk_values=(val("max_drawdown"),val("volatility"));risk=0 if all(value is None for value in risk_values) else 100-(_bounded(abs(risk_values[0] or 0),0,10000)+_bounded(risk_values[1],0,15000))/2
    consistency_values=(val("sharpe"),val("sortino"));consistency=0 if all(value is None for value in consistency_values) else (_bounded(consistency_values[0],-1,3)+_bounded(consistency_values[1],-1,4))/2
    robustness_evidence=profile.get("robustness",{});robust_states=[]
    for key in ("walk_forward","live_backtest_divergence","parameter_sensitivity"):
        value=robustness_evidence.get(key)
        if isinstance(value,dict):robust_states.append(value.get("state"))
    robustness=100*sum(state=="VALID" for state in robust_states)/len(robust_states) if robust_states else 50*float(evidence["confidence"])
    evidence_score=100*float(evidence["confidence"])
    components={"performance":performance,"risk":risk,"consistency":consistency,"robustness":robustness,"evidence":evidence_score}
    quality=sum(components[k]*WEIGHTS[k] for k in WEIGHTS)
    critical_complete=not all(value is None for value in risk_values) and not all(value is None for value in consistency_values);confidence=round(evidence_score,2);band="insufficient evidence" if confidence<30 or not critical_complete else "high" if quality>=75 else "medium" if quality>=50 else "low"
    return {"version":SCORE_VERSION,"quality_score":round(quality,2),"quality_band":band,"components":{k:round(v,2) for k,v in components.items()},
            "weights":WEIGHTS,"confidence":confidence,"rank_eligible":confidence>=30 and critical_complete,"missing_critical_components":[] if critical_complete else ["sequence risk","risk-adjusted consistency"],"explanation":[f"{k.title()} contributes {components[k]*WEIGHTS[k]:.1f} points" for k in WEIGHTS]}


def percentile(value:float,cohort:list[float])->float|None:
    clean=sorted(float(x) for x in cohort if x is not None and math.isfinite(float(x)))
    if len(clean)<2:return None
    below=sum(x<value for x in clean); equal=sum(x==value for x in clean)
    return round(100*(below+0.5*equal)/len(clean),2)


def cohort_percentiles(records:list[dict],metric:str,cohort_keys=("family","asset_class","instrument","track_record"),minimum_size=5)->dict:
    """Return stable midrank percentiles and suppress cohorts that are too small."""
    valid=[r for r in records if r.get(metric) is not None];output={}
    for row in valid:
        membership={"all":"all"}
        for key in cohort_keys:
            if row.get(key) is not None:membership[key]=str(row[key])
        result={}
        for key,value in membership.items():
            peers=valid if key=="all" else [x for x in valid if str(x.get(key))==value]
            safe=len(peers)>=minimum_size
            result[key]={"cohort":value,"size":len(peers),"percentile":percentile(row[metric],[x[metric] for x in peers]) if safe else None,
                         "state":"VALID" if safe else "INSUFFICIENT_COHORT"}
        output[row["strategy_id"]]=result
    return output


def correlation(a:list,b:list)->dict:
    """Correlate aligned observations; dict inputs must provide timestamp and return."""
    aligned=False
    if a and b and isinstance(a[0],dict) and isinstance(b[0],dict):
        left={str(item["timestamp"]):float(item["return"]) for item in a};right={str(item["timestamp"]):float(item["return"]) for item in b}
        keys=sorted(set(left)&set(right));x=[left[key] for key in keys];y=[right[key] for key in keys];aligned=True
    else:
        count=min(len(a),len(b));x=[float(v) for v in a[:count]];y=[float(v) for v in b[:count]]
    count=len(x)
    if count<3 or statistics.pstdev(x)==0 or statistics.pstdev(y)==0:return {"value":None,"overlap":count,"confidence":"insufficient"}
    value=statistics.correlation(x,y)
    return {"value":round(value,6),"overlap":count,"confidence":"high" if count>=30 else "low","timestamp_aligned":aligned}


def rolling_correlation(a:list[dict],b:list[dict],window=30)->list[dict]:
    left={str(item["timestamp"]):float(item["return"]) for item in a};right={str(item["timestamp"]):float(item["return"]) for item in b};keys=sorted(set(left)&set(right));out=[]
    for end in range(window,len(keys)+1):
        selected=keys[end-window:end];result=correlation([left[key] for key in selected],[right[key] for key in selected]);out.append({"through":selected[-1],**result})
    return out


def correlation_matrix(series:dict[str,list[dict]])->dict:
    ids=sorted(series);cells=[]
    for index,left in enumerate(ids):
        cells.append({"left":left,"right":left,"value":1.0,"overlap":len(series[left]),"confidence":"self"})
        for right in ids[index+1:]:cells.append({"left":left,"right":right,**correlation(series[left],series[right])})
    return {"version":SCORE_VERSION,"strategy_ids":ids,"cells":cells}


def similarity(left:dict,right:dict,features=("quality_score","win_rate","profit_factor","max_drawdown"),cohort:list[dict]|None=None)->dict:
    contributions={}; total=0.0
    for key in features:
        a=left.get(key); b=right.get(key)
        if a is None or b is None:continue
        peers=[float(row[key]) for row in (cohort or []) if row.get(key) is not None];scale=statistics.pstdev(peers) if len(peers)>1 else max(1.0,abs(float(a)),abs(float(b)));scale=scale or 1.0;distance=abs(float(a)-float(b))/scale
        contributions[key]=round(distance,6); total+=distance*distance
    distance=math.sqrt(total/max(1,len(contributions)))
    return {"similarity":round(max(0,100*(1-distance)),2),"distance":round(distance,6),"contributions":contributions}


def related_strategies(target:dict,candidates:list[dict],limit=5)->list[dict]:
    rows=[]
    for candidate in candidates:
        if candidate.get("strategy_id")==target.get("strategy_id"):continue
        result=similarity(target,candidate,cohort=[target,*candidates]);rows.append({"strategy_id":candidate["strategy_id"],**result,"reasons":[f"{key} distance {value:.3f}" for key,value in result["contributions"].items()]})
    return sorted(rows,key=lambda row:(-row["similarity"],row["strategy_id"]))[:limit]
