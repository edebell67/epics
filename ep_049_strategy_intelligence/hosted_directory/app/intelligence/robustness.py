"""Behaviour and robustness evidence with strict sample eligibility.

VERSION HISTORY
v1.0.1 (2026-09-04) - Relocated from epics/ep_051_strategy_directory/hosted_directory/ to epics/ep_049_strategy_intelligence/hosted_directory/ per Ed's EP049 ownership decision. No code changes.
v1.0.0 · 2026-08-24 · Holding/exposure, sensitivity, walk-forward and divergence metrics.
"""
from __future__ import annotations
from datetime import datetime
import statistics


def _time(value):return value if isinstance(value,datetime) else datetime.fromisoformat(str(value).replace("Z","+00:00"))


def trade_behaviour(trades,minimum=5):
    valid=[row for row in trades if row.get("opened_at") and row.get("closed_at") and _time(row["closed_at"])>=_time(row["opened_at"])]
    if len(valid)<minimum:return {"state":"COLLECTING","sample_count":len(valid),"median_hold_minutes":None,"mean_hold_minutes":None,"exposure_fraction":None}
    holds=[(_time(row["closed_at"])-_time(row["opened_at"])).total_seconds()/60 for row in valid]
    start=min(_time(row["opened_at"]) for row in valid);end=max(_time(row["closed_at"]) for row in valid)
    intervals=sorted((_time(row["opened_at"]),_time(row["closed_at"])) for row in valid);merged=[]
    for left,right in intervals:
        if not merged or left>merged[-1][1]:merged.append([left,right])
        else:merged[-1][1]=max(merged[-1][1],right)
    occupied=sum((right-left).total_seconds() for left,right in merged);window=(end-start).total_seconds()
    return {"state":"VALID","sample_count":len(valid),"median_hold_minutes":statistics.median(holds),"mean_hold_minutes":statistics.mean(holds),"exposure_fraction":occupied/window if window>0 else None}


def parameter_sensitivity(runs,minimum=5):
    scores=[float(row["score"]) for row in runs if row.get("score") is not None]
    if len(scores)<minimum:return {"state":"COLLECTING","sample_count":len(scores),"score_cv":None}
    mean=statistics.mean(scores);return {"state":"VALID","sample_count":len(scores),"score_cv":statistics.pstdev(scores)/abs(mean) if mean else None,"stable":bool(mean) and statistics.pstdev(scores)/abs(mean)<=.25}


def walk_forward(folds,minimum=3):
    eligible=[row for row in folds if _time(row["train_end"])<_time(row["test_start"])]
    if len(eligible)!=len(folds):return {"state":"INVALID","reason":"LEAKAGE","folds":len(folds)}
    if len(folds)<minimum:return {"state":"COLLECTING","folds":len(folds)}
    returns=[float(row["test_return"]) for row in folds];return {"state":"VALID","folds":len(folds),"positive_fold_rate":sum(value>0 for value in returns)/len(returns),"mean_test_return":statistics.mean(returns)}


def live_backtest_divergence(backtest,live,minimum=20):
    if len(backtest)<minimum or len(live)<minimum:return {"state":"COLLECTING","backtest_count":len(backtest),"live_count":len(live),"mean_shift":None}
    baseline=statistics.mean(map(float,backtest));observed=statistics.mean(map(float,live));scale=statistics.pstdev(map(float,backtest)) or 1
    shift=(observed-baseline)/scale;return {"state":"VALID","backtest_count":len(backtest),"live_count":len(live),"mean_shift":shift,"alert":abs(shift)>=1}


def walk_forward_folds_from_points(points,folds=4,return_basis="net_return"):
    """Derive chronological walk-forward folds directly from an evidence window's
    trade points, so walk_forward() re-windows naturally with whatever `points`
    (e.g. an as-of-bounded set) is passed in, instead of depending on a separate
    offline fold table. Splits points into `folds` contiguous chronological
    chunks; each chunk after the first becomes one out-of-sample test fold
    against everything before it, so train_end < test_start always holds.
    `return_basis` selects which outcome column each fold's test_return sums -
    net_return (as-traded) or alt_net_return (the same trades reversed)."""
    eligible=[row for row in points if row.get(return_basis) is not None]
    ordered=sorted((row for row in eligible if row.get("closed_at")),key=lambda row:_time(row["closed_at"]))
    if len(ordered)<folds*2:return []
    size=len(ordered)//folds;chunks=[ordered[i*size:(i+1)*size] for i in range(folds-1)]+[ordered[(folds-1)*size:]]
    result=[]
    for previous,current in zip(chunks,chunks[1:]):
        train_end=_time(previous[-1]["closed_at"]);test_start=_time(current[0]["closed_at"])
        if test_start<=train_end:continue
        result.append({"train_end":train_end.isoformat(),"test_start":test_start.isoformat(),"test_return":sum(float(row[return_basis]) for row in current)})
    return result


def divergence_split_from_points(points,minimum=20,return_basis="net_return"):
    """Split an evidence window's trade points chronologically in half so
    live_backtest_divergence() can measure whether the strategy's second half
    diverged from its first half within that same window - the closest
    signal available without a separately tracked backtest/live source.
    `return_basis` selects net_return (as-traded) or alt_net_return (every
    trade reversed)."""
    eligible=[row for row in points if row.get(return_basis) is not None]
    ordered=sorted((row for row in eligible if row.get("closed_at")),key=lambda row:_time(row["closed_at"]))
    if len(ordered)<minimum*2:return [],[]
    mid=len(ordered)//2
    return [float(row[return_basis]) for row in ordered[:mid]],[float(row[return_basis]) for row in ordered[mid:]]
